"""
日刊スポーツ マークダウン変換ツール
Streamlit Community Cloud対応版
"""

import streamlit as st
import yaml
import os
from datetime import datetime
from pathlib import Path
import hashlib

# ローカルモジュールのインポート
from src.word_reader import extract_text_only
from src.converter import convert_to_markdown, proofread_article


# ページ設定
st.set_page_config(
    page_title="日刊スポーツ マークダウン変換ツール",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =============================================================================
# Streamlit Cloud Secrets対応
# =============================================================================

def get_api_key():
    """APIキーを取得（Secrets または 環境変数）"""
    # Streamlit Secretsから取得を試みる
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass
    
    # 環境変数から取得
    return os.getenv('ANTHROPIC_API_KEY')


def get_initial_users():
    """初期ユーザーをSecretsから取得"""
    try:
        return dict(st.secrets["users"])
    except (KeyError, FileNotFoundError):
        # デフォルトの管理者アカウント
        return {
            "admin": {
                "name": "管理者",
                "password": hash_password("admin123"),
                "role": "admin"
            }
        }


# =============================================================================
# ユーティリティ関数
# =============================================================================

def load_config():
    """アプリ設定を読み込む"""
    config_path = Path(__file__).parent / 'config' / 'config.yaml'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def hash_password(password: str) -> str:
    """パスワードをハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """パスワードを検証"""
    return hash_password(password) == hashed


def get_users():
    """ユーザー一覧を取得"""
    if 'users_db' not in st.session_state:
        st.session_state['users_db'] = get_initial_users()
    return st.session_state['users_db']


def add_user(username, name, password, role):
    """ユーザーを追加"""
    users = get_users()
    users[username] = {
        "name": name,
        "password": hash_password(password),
        "role": role
    }
    st.session_state['users_db'] = users


def delete_user(username):
    """ユーザーを削除"""
    users = get_users()
    if username in users and username != 'admin':
        del users[username]
        st.session_state['users_db'] = users


# =============================================================================
# カスタムCSS
# =============================================================================

def load_css():
    st.markdown("""
    <style>
        .main-header {
            font-size: 2rem;
            font-weight: bold;
            color: #1e3a5f;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            font-size: 1rem;
            color: #666;
            margin-bottom: 2rem;
        }
        .user-info {
            padding: 0.5rem 1rem;
            background-color: #e7f3ff;
            border-radius: 5px;
            margin-bottom: 1rem;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# ログインページ
# =============================================================================

def login_page():
    """ログインページ"""
    st.markdown('<p class="main-header">📰 日刊スポーツ マークダウン変換ツール</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">ログインしてください</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("ユーザー名", placeholder="ユーザー名を入力")
            password = st.text_input("パスワード", type="password", placeholder="パスワードを入力")
            
            submit = st.form_submit_button("ログイン", use_container_width=True)
            
            if submit:
                users = get_users()
                
                if username in users:
                    stored_password = users[username].get('password', '')
                    
                    if verify_password(password, stored_password):
                        st.session_state['authenticated'] = True
                        st.session_state['username'] = username
                        st.session_state['user_name'] = users[username].get('name', username)
                        st.session_state['user_role'] = users[username].get('role', 'user')
                        st.rerun()
                    else:
                        st.error("❌ パスワードが正しくありません")
                else:
                    st.error("❌ ユーザーが見つかりません")
        
        with st.expander("💡 初期ログイン情報"):
            st.info("""
            **管理者アカウント**
            - ユーザー名: `admin`
            - パスワード: `admin123`
            
            ※初回ログイン後にユーザーを追加してください
            """)


# =============================================================================
# メインページ（変換機能）
# =============================================================================

def main_page():
    """メインページ（変換機能）"""
    config = load_config()
    
    # ヘッダー
    col_header1, col_header2 = st.columns([3, 1])
    
    with col_header1:
        st.markdown('<p class="main-header">📰 日刊スポーツ マークダウン変換ツール</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Word原稿を日刊スポーツ規定のマークダウン形式に変換します</p>', unsafe_allow_html=True)
    
    with col_header2:
        st.markdown(f'<div class="user-info">👤 {st.session_state.get("user_name", "ユーザー")}</div>', unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.session_state.get('user_role') == 'admin':
                if st.button("⚙️ 管理", use_container_width=True):
                    st.session_state['page'] = 'admin'
                    st.rerun()
        with col_btn2:
            if st.button("🚪 ログアウト", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key != 'users_db':  # ユーザーDBは保持
                        del st.session_state[key]
                st.rerun()
    
    # APIキーの確認
    api_key = get_api_key()
    
    if not api_key:
        st.error("""
        ⚠️ **ANTHROPIC_API_KEY が設定されていません**
        
        Streamlit CloudのSecretsに以下を設定してください：
        ```
        ANTHROPIC_API_KEY = "sk-ant-xxxxxxxxxxxxx"
        ```
        """)
        return
    
    st.divider()
    
    # メインコンテンツ（2カラム）
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 Word原稿をアップロード")
        
        uploaded_file = st.file_uploader(
    "原稿ファイルをドラッグ＆ドロップ、またはクリックして選択",
    type=['docx', 'txt'],
    help="Word形式（.docx）またはテキスト形式（.txt）に対応"
)
            help="日刊スポーツの記事原稿（Word形式）をアップロードしてください"
        )
        
        st.subheader("⚙️ 設定（任意）")
        
        reporter_name = st.text_input("記者名", placeholder="例：山田太郎")
        
        do_proofread = st.checkbox("校閲チェックを実行", value=True)
        
        st.divider()
        convert_button = st.button("🔄 変換実行", type="primary", use_container_width=True)
    
    with col2:
        st.subheader("📝 変換結果")
        
        if convert_button and uploaded_file is not None:
            with st.spinner("変換中...（30秒〜1分程度）"):
                try:
                    file_bytes = uploaded_file.read()
                   # ファイル形式を判定
file_type = "txt" if uploaded_file.name.endswith('.txt') else "docx"
article_text = extract_text_only(file_bytes, file_type)
                    
                    if not article_text.strip():
                        st.error("❌ Word原稿からテキストを抽出できませんでした")
                        return
                    
                    result = convert_to_markdown(
                        article_text=article_text,
                        reporter_name=reporter_name,
                        api_key=api_key
                    )
                    
                    if result['success']:
                        st.success("✅ 変換完了")
                        
                        st.text_area(
                            "変換後のマークダウン",
                            value=result['markdown'],
                            height=400
                        )
                        
                        st.session_state['markdown_result'] = result['markdown']
                        st.session_state['original_filename'] = uploaded_file.name
                        
                        if do_proofread:
                            with st.spinner("校閲チェック中..."):
                                proofread_result = proofread_article(
                                    markdown_text=result['markdown'],
                                    api_key=api_key
                                )
                                
                                if proofread_result['success']:
                                    st.session_state['proofread_report'] = proofread_result['report']
                                    
                                    if proofread_result['issues_count'] > 0:
                                        st.warning(f"⚠️ 校閲で {proofread_result['issues_count']} 件の指摘があります")
                                    else:
                                        st.info("ℹ️ 校閲チェック完了：問題なし")
                    else:
                        st.error(f"❌ 変換エラー: {result['error']}")
                        
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")
        
        elif convert_button and uploaded_file is None:
            st.warning("⚠️ Word原稿をアップロードしてください")
        
        # ダウンロードボタン
        if 'markdown_result' in st.session_state:
            st.divider()
            st.subheader("📥 ダウンロード")
            
            original_name = st.session_state.get('original_filename', 'article')
            base_name = original_name.rsplit('.', 1)[0]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                st.download_button(
                    label="📄 マークダウン.txt",
                    data=st.session_state['markdown_result'],
                    file_name=f"{base_name}_{timestamp}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col_dl2:
                if 'proofread_report' in st.session_state:
                    st.download_button(
                        label="📋 校閲レポート.txt",
                        data=st.session_state['proofread_report'],
                        file_name=f"{base_name}_校閲レポート_{timestamp}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
        
        if 'proofread_report' in st.session_state:
            with st.expander("📋 校閲レポートを表示"):
                st.text_area("校閲レポート", value=st.session_state['proofread_report'], height=300, disabled=True)
    
    # フッター
    st.divider()
    st.markdown('<div style="text-align: center; color: #888;">日刊スポーツ マークダウン変換ツール v1.0 | 変換ルール ver.4 準拠</div>', unsafe_allow_html=True)


# =============================================================================
# 管理者ページ
# =============================================================================

def admin_page():
    """管理者ページ"""
    st.markdown('<p class="main-header">⚙️ 管理者画面</p>', unsafe_allow_html=True)
    
    if st.button("← メイン画面に戻る"):
        st.session_state['page'] = 'main'
        st.rerun()
    
    st.divider()
    
    st.subheader("👥 ユーザー管理")
    
    users = get_users()
    
    # ユーザー一覧
    st.write("**現在のユーザー：**")
    for username, user_info in users.items():
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        
        with col1:
            st.write(f"**{user_info.get('name', username)}**")
        with col2:
            st.write(f"`{username}`")
        with col3:
            role = user_info.get('role', 'user')
            st.write("🔑 管理者" if role == 'admin' else "👤 一般")
        with col4:
            if username != 'admin':
                if st.button("🗑️", key=f"del_{username}"):
                    delete_user(username)
                    st.success(f"✅ {username} を削除しました")
                    st.rerun()
    
    st.divider()
    
    # ユーザー追加
    st.subheader("➕ ユーザー追加")
    
    with st.form("add_user_form"):
        new_username = st.text_input("ユーザー名（ログインID）", placeholder="例: tanaka")
        new_name = st.text_input("表示名", placeholder="例: 田中太郎")
        new_password = st.text_input("パスワード", type="password")
        new_role = st.selectbox("権限", ["user", "admin"], format_func=lambda x: "一般ユーザー" if x == "user" else "管理者")
        
        if st.form_submit_button("追加"):
            if new_username and new_name and new_password:
                if new_username in users:
                    st.error("❌ このユーザー名は既に使用されています")
                else:
                    add_user(new_username, new_name, new_password, new_role)
                    st.success(f"✅ {new_name} を追加しました")
                    st.rerun()
            else:
                st.error("❌ すべての項目を入力してください")
    
    # 注意事項
    st.divider()
    st.warning("""
    ⚠️ **注意事項**
    
    Streamlit Community Cloudでは、アプリが再起動するとユーザー情報がリセットされます。
    
    永続的にユーザーを管理するには、Streamlit Secretsに以下の形式で設定してください：
    
    ```toml
    [users.yamada]
    name = "山田太郎"
    password = "ハッシュ化されたパスワード"
    role = "user"
    ```
    """)


# =============================================================================
# メイン処理
# =============================================================================

def main():
    """メイン処理"""
    load_css()
    
    # 認証チェック
    if not st.session_state.get('authenticated', False):
        login_page()
        return
    
    # ページルーティング
    page = st.session_state.get('page', 'main')
    
    if page == 'admin' and st.session_state.get('user_role') == 'admin':
        admin_page()
    else:
        main_page()


if __name__ == "__main__":
    main()
