"""
日刊スポーツ 変換ツール
Streamlit Community Cloud対応版
マークダウン変換・一問一答変換対応
"""

import streamlit as st
import yaml
import os
from datetime import datetime
from pathlib import Path
import hashlib

from src.word_reader import extract_text_only
from src.converter import (
    convert_to_markdown, 
    convert_to_qa,
    proofread_article, 
    proofread_qa,
    revise_markdown,
    revise_qa
)


st.set_page_config(
    page_title="日刊スポーツ 変換ツール",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="collapsed"
)


def get_api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass
    return os.getenv('ANTHROPIC_API_KEY')


def get_initial_users():
    try:
        return dict(st.secrets["users"])
    except (KeyError, FileNotFoundError):
        return {
            "admin": {
                "name": "管理者",
                "password": hash_password("admin123"),
                "role": "admin"
            }
        }


def load_config():
    config_path = Path(__file__).parent / 'config' / 'config.yaml'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def get_users():
    if 'users_db' not in st.session_state:
        st.session_state['users_db'] = get_initial_users()
    return st.session_state['users_db']


def add_user(username, name, password, role):
    users = get_users()
    users[username] = {
        "name": name,
        "password": hash_password(password),
        "role": role
    }
    st.session_state['users_db'] = users


def delete_user(username):
    users = get_users()
    if username in users and username != 'admin':
        del users[username]
        st.session_state['users_db'] = users


def clear_workspace():
    """作業スペースをクリアする"""
    keys_to_clear = [
        # 変換結果
        'markdown_result',
        'qa_result',
        'original_filename',
        'original_article',
        'revision_history',
        'qa_revision_history',
        'proofread_report',
        'qa_proofread_report',
        'qa_filename',
        # 入力エリアの値
        'md_article_input',
        'qa_article_input',
        'md_reporter',
        'md_revision_input',
        'qa_revision_input',
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # ウィジェットのキーをインクリメントして強制リセット
    # Streamlitはキーが変わると新しいウィジェットとして再描画するため入力値がクリアされる
    st.session_state['widget_key'] = st.session_state.get('widget_key', 0) + 1


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
        .revision-history {
            background-color: #f8f9fa;
            border-left: 3px solid #1e3a5f;
            padding: 0.5rem 1rem;
            margin: 0.5rem 0;
            font-size: 0.9rem;
        }
    </style>
    """, unsafe_allow_html=True)


@st.dialog("📖 機能一覧")
def show_features():
    """機能一覧をポップアップ表示"""
    st.markdown("""
### 【📝 マークダウン変換】
- Word / テキスト原稿をマークダウン形式に変換
- サマリーの「です・ます調」への自動変換
- 見所3点（##mokuji-2##）の抽出
- 中見出しの自動生成
- 写真タグ（▲▲写真▲▲）の自動挿入
- 有料区切り（==members_12==）の配置
- 英数字の半角統一

### 【💬 一問一答変換】
- 音声文字起こしを一問一答形式に変換
- 質問部分の敬体→常体変換
- フィラー・表記の自動調整

### 【共通機能】
- 変換後の修正リクエスト（自然な言葉で依頼可）
- 校閲チェック（誤字脱字の検出）
- テキストファイル出力
    """)


def login_page():
    st.markdown('<p class="main-header">📰 日刊スポーツ 変換ツール</p>', unsafe_allow_html=True)
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
            """)


def main_page():
    config = load_config()
    
    # ヘッダー
    col_header1, col_header2 = st.columns([3, 1])
    
    with col_header1:
        st.markdown('<p class="main-header">📰 日刊スポーツ 変換ツール</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">原稿を指定の形式に変換します</p>', unsafe_allow_html=True)
    
    with col_header2:
        st.markdown(f'<div class="user-info">👤 {st.session_state.get("user_name", "ユーザー")}</div>', unsafe_allow_html=True)
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("📖 機能一覧", use_container_width=True):
                show_features()
        with col_btn2:
            if st.session_state.get('user_role') == 'admin':
                if st.button("⚙️ 管理", use_container_width=True):
                    st.session_state['page'] = 'admin'
                    st.rerun()
        with col_btn3:
            if st.button("🚪 ログアウト", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key != 'users_db':
                        del st.session_state[key]
                st.rerun()
    
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
    
    # タブ切り替え
    tab1, tab2 = st.tabs(["📝 マークダウン変換", "💬 一問一答変換"])
    
    # マークダウン変換タブ
    with tab1:
        markdown_tab(api_key)
    
    # 一問一答変換タブ
    with tab2:
        qa_tab(api_key)
    
    # フッター
    st.divider()
    st.markdown('<div style="text-align: center; color: #888;">日刊スポーツ 変換ツール v2.0</div>', unsafe_allow_html=True)


def markdown_tab(api_key):
    """マークダウン変換タブの内容"""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 原稿を入力")
        
        input_method = st.radio(
            "入力方法を選択",
            ["テキストを直接入力", "ファイルをアップロード"],
            horizontal=True,
            key="md_input_method"
        )
        
        article_text = ""
        filename = "article"
        
        # クリア時にウィジェットを再描画するためのキー
        wk = st.session_state.get('widget_key', 0)

        if input_method == "テキストを直接入力":
            article_text = st.text_area(
                "原稿をコピー＆ペースト",
                height=300,
                placeholder="ここに記事の原稿を貼り付けてください...",
                key=f"md_article_input_{wk}"
            )
            filename = "markdown"
        else:
            uploaded_file = st.file_uploader(
                "原稿ファイルをドラッグ＆ドロップ、またはクリックして選択",
                type=['docx', 'txt'],
                help="Word形式（.docx）またはテキスト形式（.txt）に対応",
                key="md_file_upload"
            )
            if uploaded_file is not None:
                file_bytes = uploaded_file.read()
                file_type = "txt" if uploaded_file.name.endswith('.txt') else "docx"
                article_text = extract_text_only(file_bytes, file_type)
                filename = uploaded_file.name.rsplit('.', 1)[0]
        
        st.subheader("⚙️ 設定（任意）")
        
        reporter_name = st.text_input("記者名", placeholder="例：山田太郎", key="md_reporter")
        
        do_proofread = st.checkbox("校閲チェックを実行", value=True, key="md_proofread")
        
        st.divider()
        
        col_btn1, col_btn2 = st.columns([2, 1])
        
        with col_btn1:
            convert_button = st.button("🔄 変換実行", type="primary", use_container_width=True, key="md_convert")
        
        with col_btn2:
            clear_button = st.button("🗑️ クリア", use_container_width=True, key="md_clear")
        
        if clear_button:
            clear_workspace()
            st.success("✅ クリアしました")
            st.rerun()
        
        if convert_button:
            st.session_state['revision_history'] = []
    
    with col2:
        st.subheader("📝 変換結果")
        
        if convert_button:
            if not article_text.strip():
                st.warning("⚠️ 原稿を入力またはアップロードしてください")
            else:
                with st.spinner("変換中...（30秒〜1分程度）"):
                    try:
                        result = convert_to_markdown(
                            article_text=article_text,
                            reporter_name=reporter_name,
                            api_key=api_key
                        )
                        
                        if result['success']:
                            st.success("✅ 変換完了")
                            
                            st.session_state['markdown_result'] = result['markdown']
                            st.session_state['original_filename'] = filename
                            st.session_state['original_article'] = article_text
                            st.session_state['revision_history'] = []
                            
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
        
        # 変換結果の表示
        if 'markdown_result' in st.session_state:
            st.text_area(
                "変換後のマークダウン",
                value=st.session_state['markdown_result'],
                height=400,
                key="md_display"
            )
            
            # 修正履歴の表示
            if 'revision_history' in st.session_state and st.session_state['revision_history']:
                with st.expander(f"📋 修正履歴（{len(st.session_state['revision_history'])}件）"):
                    for i, revision in enumerate(st.session_state['revision_history'], 1):
                        st.markdown(f'<div class="revision-history"><strong>修正{i}:</strong> {revision}</div>', unsafe_allow_html=True)
            
            st.divider()
            
            # 修正リクエスト機能
            st.subheader("🔄 修正リクエスト")
            
            revision_request = st.text_area(
                "修正したい内容を入力",
                height=100,
                placeholder="例：\n・3つ目の見出しを「新シーズンへの意気込み」に変えて\n・サマリーをもう少し短くして",
                key="md_revision_input"
            )
            
            revise_button = st.button("✏️ 修正を実行", use_container_width=True, key="md_revise")
            
            if revise_button:
                if not revision_request.strip():
                    st.warning("⚠️ 修正内容を入力してください")
                else:
                    with st.spinner("修正中..."):
                        try:
                            revision_result = revise_markdown(
                                markdown_text=st.session_state['markdown_result'],
                                revision_request=revision_request,
                                api_key=api_key
                            )
                            
                            if revision_result['success']:
                                st.success("✅ 修正完了")
                                
                                if 'revision_history' not in st.session_state:
                                    st.session_state['revision_history'] = []
                                st.session_state['revision_history'].append(revision_request)
                                
                                st.session_state['markdown_result'] = revision_result['markdown']
                                st.rerun()
                            else:
                                st.error(f"❌ 修正エラー: {revision_result['error']}")
                                
                        except Exception as e:
                            st.error(f"❌ エラーが発生しました: {str(e)}")
            
            st.divider()
            st.subheader("📥 ダウンロード")
            
            base_name = st.session_state.get('original_filename', 'article')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                st.download_button(
                    label="📄 マークダウン.txt",
                    data=st.session_state['markdown_result'],
                    file_name=f"{base_name}_{timestamp}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="md_download"
                )
            
            with col_dl2:
                if 'proofread_report' in st.session_state:
                    st.download_button(
                        label="📋 校閲レポート.txt",
                        data=st.session_state['proofread_report'],
                        file_name=f"{base_name}_校閲レポート_{timestamp}.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key="md_proofread_download"
                    )
        
        if 'proofread_report' in st.session_state:
            with st.expander("📋 校閲レポートを表示"):
                st.text_area("校閲レポート", value=st.session_state['proofread_report'], height=300, disabled=True, key="md_proofread_display")


def qa_tab(api_key):
    """一問一答変換タブの内容"""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 原稿を入力")
        
        input_method = st.radio(
            "入力方法を選択",
            ["テキストを直接入力", "ファイルをアップロード"],
            horizontal=True,
            key="qa_input_method"
        )
        
        article_text = ""
        filename = "qa"
        
        # クリア時にウィジェットを再描画するためのキー
        wk = st.session_state.get('widget_key', 0)

        if input_method == "テキストを直接入力":
            article_text = st.text_area(
                "音声文字起こしをコピー＆ペースト",
                height=300,
                placeholder="ここに音声文字起こしを貼り付けてください...",
                key=f"qa_article_input_{wk}"
            )
            filename = "qa"
        else:
            uploaded_file = st.file_uploader(
                "原稿ファイルをドラッグ＆ドロップ、またはクリックして選択",
                type=['docx', 'txt'],
                help="Word形式（.docx）またはテキスト形式（.txt）に対応",
                key="qa_file_upload"
            )
            if uploaded_file is not None:
                file_bytes = uploaded_file.read()
                file_type = "txt" if uploaded_file.name.endswith('.txt') else "docx"
                article_text = extract_text_only(file_bytes, file_type)
                filename = uploaded_file.name.rsplit('.', 1)[0]
        
        do_proofread = st.checkbox("校閲チェックを実行", value=True, key="qa_proofread")
        
        st.divider()
        
        col_btn1, col_btn2 = st.columns([2, 1])
        
        with col_btn1:
            convert_button = st.button("🔄 変換実行", type="primary", use_container_width=True, key="qa_convert")
        
        with col_btn2:
            clear_button = st.button("🗑️ クリア", use_container_width=True, key="qa_clear")
        
        if clear_button:
            clear_workspace()
            st.success("✅ クリアしました")
            st.rerun()
        
        if convert_button:
            st.session_state['qa_revision_history'] = []
    
    with col2:
        st.subheader("📝 変換結果")
        
        if convert_button:
            if not article_text.strip():
                st.warning("⚠️ 原稿を入力またはアップロードしてください")
            else:
                with st.spinner("変換中...（30秒〜1分程度）"):
                    try:
                        result = convert_to_qa(
                            article_text=article_text,
                            api_key=api_key
                        )
                        
                        if result['success']:
                            st.success("✅ 変換完了")
                            
                            st.session_state['qa_result'] = result['qa_text']
                            st.session_state['qa_filename'] = filename
                            st.session_state['qa_revision_history'] = []
                            
                            if do_proofread:
                                with st.spinner("校閲チェック中..."):
                                    proofread_result = proofread_qa(
                                        qa_text=result['qa_text'],
                                        api_key=api_key
                                    )
                                    
                                    if proofread_result['success']:
                                        st.session_state['qa_proofread_report'] = proofread_result['report']
                                        
                                        if proofread_result['issues_count'] > 0:
                                            st.warning(f"⚠️ 校閲で {proofread_result['issues_count']} 件の指摘があります")
                                        else:
                                            st.info("ℹ️ 校閲チェック完了：問題なし")
                        else:
                            st.error(f"❌ 変換エラー: {result['error']}")
                            
                    except Exception as e:
                        st.error(f"❌ エラーが発生しました: {str(e)}")
        
        # 変換結果の表示
        if 'qa_result' in st.session_state:
            st.text_area(
                "変換後の一問一答",
                value=st.session_state['qa_result'],
                height=400,
                key="qa_display"
            )
            
            # 修正履歴の表示
            if 'qa_revision_history' in st.session_state and st.session_state['qa_revision_history']:
                with st.expander(f"📋 修正履歴（{len(st.session_state['qa_revision_history'])}件）"):
                    for i, revision in enumerate(st.session_state['qa_revision_history'], 1):
                        st.markdown(f'<div class="revision-history"><strong>修正{i}:</strong> {revision}</div>', unsafe_allow_html=True)
            
            st.divider()
            
            # 修正リクエスト機能
            st.subheader("🔄 修正リクエスト")
            
            revision_request = st.text_area(
                "修正したい内容を入力",
                height=100,
                placeholder="例：\n・3つ目の質問を削除して\n・回答の表記を修正して",
                key="qa_revision_input"
            )
            
            revise_button = st.button("✏️ 修正を実行", use_container_width=True, key="qa_revise")
            
            if revise_button:
                if not revision_request.strip():
                    st.warning("⚠️ 修正内容を入力してください")
                else:
                    with st.spinner("修正中..."):
                        try:
                            revision_result = revise_qa(
                                qa_text=st.session_state['qa_result'],
                                revision_request=revision_request,
                                api_key=api_key
                            )
                            
                            if revision_result['success']:
                                st.success("✅ 修正完了")
                                
                                if 'qa_revision_history' not in st.session_state:
                                    st.session_state['qa_revision_history'] = []
                                st.session_state['qa_revision_history'].append(revision_request)
                                
                                st.session_state['qa_result'] = revision_result['qa_text']
                                st.rerun()
                            else:
                                st.error(f"❌ 修正エラー: {revision_result['error']}")
                                
                        except Exception as e:
                            st.error(f"❌ エラーが発生しました: {str(e)}")
            
            st.divider()
            st.subheader("📥 ダウンロード")
            
            base_name = st.session_state.get('qa_filename', 'qa')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                st.download_button(
                    label="📄 一問一答.txt",
                    data=st.session_state['qa_result'],
                    file_name=f"{base_name}_{timestamp}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="qa_download"
                )
            
            with col_dl2:
                if 'qa_proofread_report' in st.session_state:
                    st.download_button(
                        label="📋 校閲レポート.txt",
                        data=st.session_state['qa_proofread_report'],
                        file_name=f"{base_name}_校閲レポート_{timestamp}.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key="qa_proofread_download"
                    )
        
        if 'qa_proofread_report' in st.session_state:
            with st.expander("📋 校閲レポートを表示"):
                st.text_area("校閲レポート", value=st.session_state['qa_proofread_report'], height=300, disabled=True, key="qa_proofread_display")


def admin_page():
    st.markdown('<p class="main-header">⚙️ 管理者画面</p>', unsafe_allow_html=True)
    
    if st.button("← メイン画面に戻る"):
        st.session_state['page'] = 'main'
        st.rerun()
    
    st.divider()
    
    st.subheader("👥 ユーザー管理")
    
    users = get_users()
    
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
    
    st.divider()
    st.warning("""
    ⚠️ **注意事項**
    
    Streamlit Community Cloudでは、アプリが再起動するとユーザー情報がリセットされます。
    """)


def main():
    load_css()
    
    if not st.session_state.get('authenticated', False):
        login_page()
        return
    
    page = st.session_state.get('page', 'main')
    
    if page == 'admin' and st.session_state.get('user_role') == 'admin':
        admin_page()
    else:
        main_page()


if __name__ == "__main__":
    main()
