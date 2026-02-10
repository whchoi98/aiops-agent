"""Cognito 인증 모듈 — Streamlit 대시보드용

기존 aiops-gateway-pool (gateway/setup_gateway.py에서 생성)을 재사용하며,
SSM Parameter Store에서 pool_id / client_id를 조회합니다.
"""
from __future__ import annotations

import base64
import json
import logging
from functools import lru_cache

import boto3
import streamlit as st

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cognito 설정 조회
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_cognito_config() -> dict:
    """SSM에서 Cognito User Pool 설정을 조회합니다 (캐싱).

    Returns:
        {"pool_id": str, "client_id": str, "region": str}
    """
    from agents.utils import get_ssm_parameter, SSM_PREFIX, get_aws_region

    region = get_aws_region()
    pool_id = get_ssm_parameter(f"{SSM_PREFIX}/cognito_pool_id")
    client_id = get_ssm_parameter(f"{SSM_PREFIX}/cognito_client_id")
    return {"pool_id": pool_id, "client_id": client_id, "region": region}


def _cognito_client():
    """Cognito IDP boto3 클라이언트를 반환합니다."""
    config = get_cognito_config()
    return boto3.client("cognito-idp", region_name=config["region"])


# ---------------------------------------------------------------------------
# 토큰 디코딩
# ---------------------------------------------------------------------------

def _decode_id_token(id_token: str) -> dict:
    """ID 토큰의 payload를 디코딩합니다 (서명 검증 없이 클레임만 추출).

    JWT는 header.payload.signature 형식이므로 payload 부분만 base64 디코딩.
    """
    try:
        payload_part = id_token.split(".")[1]
        # base64url 패딩 보정
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += "=" * padding
        decoded = base64.urlsafe_b64decode(payload_part)
        return json.loads(decoded)
    except Exception as e:
        logger.error(f"ID token decode failed: {e}")
        return {}


# ---------------------------------------------------------------------------
# 인증 함수
# ---------------------------------------------------------------------------

def login(username: str, password: str) -> dict | None:
    """Cognito USER_PASSWORD_AUTH로 로그인합니다.

    Returns:
        성공 시 {"username": str, "email": str, "tokens": dict}, 실패 시 None.
        NEW_PASSWORD_REQUIRED 챌린지 시 {"challenge": "NEW_PASSWORD_REQUIRED", "session": str, "username": str}.
    """
    config = get_cognito_config()
    client = _cognito_client()
    try:
        response = client.initiate_auth(
            ClientId=config["client_id"],
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
        )

        # 비밀번호 변경 챌린지 처리
        if response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            return {
                "challenge": "NEW_PASSWORD_REQUIRED",
                "session": response["Session"],
                "username": username,
            }

        tokens = response["AuthenticationResult"]
        claims = _decode_id_token(tokens["IdToken"])
        return {
            "username": claims.get("cognito:username", username),
            "email": claims.get("email", ""),
            "tokens": tokens,
        }
    except client.exceptions.NotAuthorizedException:
        st.error("사용자 이름 또는 비밀번호가 올바르지 않습니다.")
        return None
    except client.exceptions.UserNotFoundException:
        st.error("등록되지 않은 사용자입니다.")
        return None
    except Exception as e:
        st.error(f"로그인 실패: {e}")
        return None


def respond_to_new_password_challenge(
    username: str, new_password: str, session: str
) -> dict | None:
    """NEW_PASSWORD_REQUIRED 챌린지에 응답하여 비밀번호를 변경합니다."""
    config = get_cognito_config()
    client = _cognito_client()
    try:
        response = client.respond_to_auth_challenge(
            ClientId=config["client_id"],
            ChallengeName="NEW_PASSWORD_REQUIRED",
            Session=session,
            ChallengeResponses={
                "USERNAME": username,
                "NEW_PASSWORD": new_password,
            },
        )
        tokens = response["AuthenticationResult"]
        claims = _decode_id_token(tokens["IdToken"])
        return {
            "username": claims.get("cognito:username", username),
            "email": claims.get("email", ""),
            "tokens": tokens,
        }
    except Exception as e:
        st.error(f"비밀번호 변경 실패: {e}")
        return None


def signup(username: str, password: str, email: str) -> bool:
    """Cognito에 새 사용자를 등록합니다."""
    config = get_cognito_config()
    client = _cognito_client()
    try:
        client.sign_up(
            ClientId=config["client_id"],
            Username=username,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
        )
        return True
    except client.exceptions.UsernameExistsException:
        st.error("이미 존재하는 사용자 이름입니다.")
        return False
    except Exception as e:
        st.error(f"가입 실패: {e}")
        return False


def confirm_signup(username: str, code: str) -> bool:
    """이메일 인증 코드를 확인합니다."""
    config = get_cognito_config()
    client = _cognito_client()
    try:
        client.confirm_sign_up(
            ClientId=config["client_id"],
            Username=username,
            ConfirmationCode=code,
        )
        return True
    except Exception as e:
        st.error(f"인증 코드 확인 실패: {e}")
        return False


# ---------------------------------------------------------------------------
# 세션 관리
# ---------------------------------------------------------------------------

def get_current_user() -> dict | None:
    """세션에 저장된 인증 사용자 정보를 반환합니다.

    Returns:
        {"username": str, "email": str, "tokens": dict} 또는 None
    """
    return st.session_state.get("auth_user")


def logout() -> None:
    """세션 토큰 및 에이전트 상태를 초기화합니다."""
    for key in ["auth_user", "agent", "messages", "chat_session_id"]:
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# 인증 게이트 (UI)
# ---------------------------------------------------------------------------

def require_auth() -> dict | None:
    """인증되지 않은 경우 로그인/가입 UI를 표시하고 None을 반환합니다.

    인증된 경우 사용자 정보 dict를 반환합니다.
    """
    user = get_current_user()
    if user:
        return user

    # NEW_PASSWORD_REQUIRED 챌린지 진행 중인 경우
    if st.session_state.get("auth_challenge") == "NEW_PASSWORD_REQUIRED":
        _show_new_password_form()
        return None

    # 가입 후 인증 코드 입력 대기 중인 경우
    if st.session_state.get("pending_confirmation"):
        _show_confirmation_form()
        return None

    # 로그인 / 가입 탭
    login_tab, signup_tab = st.tabs(["로그인", "회원가입"])

    with login_tab:
        _show_login_form()

    with signup_tab:
        _show_signup_form()

    return None


# ---------------------------------------------------------------------------
# 내부 UI 헬퍼
# ---------------------------------------------------------------------------

def _show_login_form() -> None:
    with st.form("login_form"):
        username = st.text_input("사용자 이름")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", use_container_width=True)

    if submitted and username and password:
        result = login(username, password)
        if result:
            if result.get("challenge") == "NEW_PASSWORD_REQUIRED":
                st.session_state["auth_challenge"] = "NEW_PASSWORD_REQUIRED"
                st.session_state["auth_challenge_session"] = result["session"]
                st.session_state["auth_challenge_username"] = result["username"]
                st.info("임시 비밀번호를 변경해야 합니다.")
                st.rerun()
            else:
                st.session_state["auth_user"] = result
                st.rerun()


def _show_new_password_form() -> None:
    st.subheader("비밀번호 변경")
    st.info("관리자가 생성한 임시 비밀번호를 새 비밀번호로 변경합니다.")
    with st.form("new_password_form"):
        new_pw = st.text_input("새 비밀번호", type="password")
        confirm_pw = st.text_input("새 비밀번호 확인", type="password")
        submitted = st.form_submit_button("비밀번호 변경", use_container_width=True)

    if submitted:
        if not new_pw or not confirm_pw:
            st.error("비밀번호를 입력하세요.")
        elif new_pw != confirm_pw:
            st.error("비밀번호가 일치하지 않습니다.")
        else:
            result = respond_to_new_password_challenge(
                username=st.session_state["auth_challenge_username"],
                new_password=new_pw,
                session=st.session_state["auth_challenge_session"],
            )
            if result:
                # 챌린지 상태 정리 후 로그인 완료
                for key in [
                    "auth_challenge",
                    "auth_challenge_session",
                    "auth_challenge_username",
                ]:
                    st.session_state.pop(key, None)
                st.session_state["auth_user"] = result
                st.rerun()


def _show_signup_form() -> None:
    with st.form("signup_form"):
        username = st.text_input("사용자 이름", key="signup_username")
        email = st.text_input("이메일", key="signup_email")
        password = st.text_input("비밀번호", type="password", key="signup_password")
        submitted = st.form_submit_button("회원가입", use_container_width=True)

    if submitted and username and email and password:
        if signup(username, password, email):
            st.session_state["pending_confirmation"] = username
            st.success("가입 성공! 이메일로 전송된 인증 코드를 입력하세요.")
            st.rerun()


def _show_confirmation_form() -> None:
    st.subheader("이메일 인증")
    username = st.session_state["pending_confirmation"]
    st.info(f"**{username}** 계정의 이메일로 전송된 인증 코드를 입력하세요.")

    with st.form("confirm_form"):
        code = st.text_input("인증 코드")
        submitted = st.form_submit_button("확인", use_container_width=True)

    if submitted and code:
        if confirm_signup(username, code):
            st.session_state.pop("pending_confirmation", None)
            st.success("인증 완료! 로그인하세요.")
            st.rerun()
