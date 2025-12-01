import streamlit as st
import sqlite3
import os
from datetime import datetime
import uuid
from streamlit_js_eval import streamlit_js_eval
import hashlib


st.set_page_config(page_title="NotebookLM Clone", layout="wide")

# -----------------------------------------------------
# CSS（NotebookLM 風）
# -----------------------------------------------------
st.markdown("""
<style>
.card-container {
    position: relative;
    width: 100%;
    height: 170px;
    margin-bottom: 20px;
}

.card-body {
    width: 100%;
    height: 100%;
    border-radius: 16px;
    padding: 20px;
    box-sizing: border-box;
}

.transparent-btn {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 170px;
    opacity: 0;
}

.card-container {
    position: relative;
    width: 100%;
    height: 170px;
    margin-bottom: 25px;
}

.overlay-form {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
}

.overlay-btn {
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------
# URL → session_state 反映
# -----------------------------------------------------
query = st.query_params.to_dict()

if "page" not in st.session_state:
    st.session_state.page = "home"

if "page" in query:
    st.session_state.page = query["page"]

if "nb" in query:
    st.session_state.current_nb = query["nb"]

if "selected_uploads" not in st.session_state:
    st.session_state.selected_uploads = []

if "uploader_version" not in st.session_state:
    st.session_state.uploader_version = 0


# -----------------------------------------------------
# DB 初期化
# -----------------------------------------------------
conn = sqlite3.connect("data/notebooks.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS notebooks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    notebook_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    notebook_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# -----------------------------------------------------
# 左上ロゴ + Notebookタイトル（絶対固定）
# -----------------------------------------------------
def fixed_header(title):

    st.markdown("""
    <style>
        div[data-testid="stAppViewContainer"] {
            overflow: visible !important;
        }

        div[data-testid="stAppViewContainer"] > div:nth-child(1) {
            overflow: visible !important;
        }

        #nb-header {
            position: fixed !important;
            top: 20px !important;
            left: 20px !important;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 6px 14px;
            background: rgba(255,255,255,0.95);
            border-radius: 10px;
            z-index: 999999 !important;
            visibility: visible !important;
        }

        #nb-header img {
            width: 36px;
            height: 36px;
            cursor: pointer;
        }

        .nb-title {
            font-size: 22px;
            font-weight: 700;
            color: #333;
            user-select: none;
            cursor: default;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div id="nb-header">
        <a href="?page=home" target="_self" style="text-decoration:none;">
            <img src="https://github.com/nn-nissy1010/syokuchike/blob/main/img/Gemini_Generated_Image_6ikhsk6ikhsk6ikh.png?raw=true">
        </a>
        <span class="nb-title">{title}</span>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------
# HOME PAGE
# -----------------------------------------------------
def page_home():
    fixed_header("職人知見クラウド")
    st.markdown(
    "<h1 style='font-size:28px; margin-bottom: 0.5rem;'>職人一覧</h1>",
    unsafe_allow_html=True
    )
    cur.execute("""
        SELECT
            n.id,
            n.title,
            (SELECT COUNT(*) FROM files f WHERE f.notebook_id = n.id) AS source_count,
            n.created_at AS updated_at
        FROM notebooks n
        ORDER BY n.created_at DESC
    """)
    notebooks = cur.fetchall()

    colors = ["#E8F0FE","#EAF7EE","#FFF5E6","#FDE7EF","#E7F3F7"]
    cols_per_row = 4

    items = [("__NEW__", "", 0, None)] + notebooks

    for i, item in enumerate(items):
        if i % cols_per_row == 0:
            cols = st.columns(cols_per_row)
        col = cols[i % cols_per_row]

        with col:
            # 新規カード
            if item[0] == "__NEW__":
                st.markdown(f"""
                    <a href="?page=create" target="_self" style="text-decoration:none; color:inherit;">
                        <div style="
                            border-radius:16px;
                            margin-bottom:16px;
                            padding:30px;
                            height:160px;
                            border:2px dashed #bbb;
                            background:#f5f5f5;
                            text-align:center;
                        ">
                            <div style="font-size:40px;color:#888;">＋</div>
                            <div style="font-weight:bold;">職人を新規作成</div>
                        </div>
                    </a>
                """, unsafe_allow_html=True)
                continue

            nb_id, title, count, updated_at = item
            bg = colors[i % len(colors)]

            updated = (
                datetime.fromisoformat(updated_at).strftime("%Y/%m/%d")
                if updated_at else "更新なし"
            )

            # Notebook カード
            st.markdown(f"""
                <a href="?page=chat&nb={nb_id}" target="_self" style="text-decoration:none; color:inherit;">
                    <div style="
                        border-radius:16px;
                        margin-bottom:16px;
                        padding:20px;
                        height:160px;
                        background:{bg};
                    ">
                        <div style="font-size:16px; font-weight:bold;">{title}</div>
                        <div style="font-size:12px; color:#555;">
                            {updated}・{count}件のソース
                        </div>
                    </div>
                </a>
            """, unsafe_allow_html=True)

# -----------------------------------------------------
# CREATE PAGE
# -----------------------------------------------------
def file_hash(uploaded_file):
    uploaded_file.seek(0)
    data = uploaded_file.read()
    uploaded_file.seek(0)
    return hashlib.md5(data).hexdigest()

def render_uploaded_files():
    st.markdown("""
        <style>
            .file-card {
                border: 1px solid #eee;
                padding: 18px;
                margin-bottom: 12px;
                border-radius: 12px;
                background: #fff;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .file-name {
                font-size: 18px;
                font-weight: 600;
            }
            .del-btn {
                font-size: 22px;
                color: #888;
                background: none;
                border: none;
                cursor: pointer;
            }
            .del-btn:hover { color:#444; }
        </style>
    """, unsafe_allow_html=True)

    for i, item in enumerate(st.session_state.selected_uploads):

        col_left, col_right = st.columns([8, 1])

        with col_left:
            st.markdown(f"""
                <div class="file-name">📄 {item['name']}</div>
            """, unsafe_allow_html=True)

        with col_right:
            # ここが削除処理
            if st.button("×", key=f"del_{i}"):
                st.session_state.selected_uploads.pop(i)
                st.session_state.uploader_version += 1
                st.rerun()

def upload_ui():
    # --------------- state 初期化 ---------------
    if "selected_uploads" not in st.session_state:
        st.session_state.selected_uploads = []
    if "uploader_version" not in st.session_state:
        st.session_state.uploader_version = 0 

    # --------------- uploader の見た目だけを上書き ---------------
    st.markdown("""
        <style>
        /* ▼ アップロード枠そのものの見た目 */
        [data-testid="stFileUploaderDropzone"] {
            border: 2px dashed #c7c7c7;
            border-radius: 16px;
            padding: 48px 24px;
            background: #fbfbfb;
            color: #444;
        }

        /* 中のテキストを NotebookLM 風に差し替え */
        [data-testid="stFileUploaderDropzone"] div div::before {
            content: "📤 ソースをアップロード";
            display: block;
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 6px;
            text-align: center;
        }

        [data-testid="stFileUploaderDropzone"] div div::after {
            content: "ボタンから選択";
            display: block;
            font-size: 13px;
            opacity: 0.7;
            margin-top: 4px;
            text-align: left;
        }

        /* もともとのテキストは全部消す */
        [data-testid="stFileUploaderDropzone"] div div span,
        [data-testid="stFileUploaderDropzone"] div div small {
            display: none !important;
        }
        [data-testid="stFileUploader"] > div:last-child {
            display: none !important;
        }

        /* ボタンを丸く & テキスト日本語にする */
        [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] {
            border-radius: 999px;
            padding: 4px 18px;
            font-size: 0px;  /* 元の文字を消す */
        }

        [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"]::after {
            content: "ファイルを選択";
            font-size: 14px;
            font-weight: 600;
        }

        /* ▼ 外部連携タイトル */
        .ext-title {
            margin-top: 20px;
            margin-bottom: 8px;
            font-size: 14px;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    # --------------- 純正 uploader 本体（これ１個だけ） ---------------
    uploads = st.file_uploader(
        "ソースをアップロード",              # ラベルは CSS で消してるから何でもOK
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
        key=f"notebook_uploader_{st.session_state.uploader_version}",
        label_visibility="collapsed", 
    )

    # --------------- 追加されたファイルを state にマージ ---------------
    if uploads:
        existing = {x["hash"] for x in st.session_state.selected_uploads}
        new_items = []

        for f in uploads:
            h = file_hash(f)
            if h not in existing:
                new_items.append({
                    "name": f.name,
                    "file": f,
                    "hash": h
                })

        if new_items:
            st.session_state.selected_uploads.extend(new_items)
            st.rerun()

    # --------------- 外部連携ボタン ---------------
    st.markdown(
        '<div class="ext-title">外部サービスから追加</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        btn_drive = st.button("📂 Google ドライブ", key="ext_drive", use_container_width=True)
    with c2:
        btn_web = st.button("🌐 Salesforce", key="ext_web", use_container_width=True)
    with c3:
        btn_yt = st.button("▶️ MS Sharepoint", key="ext_yt", use_container_width=True)

    # いまはダミー動作（あとで本物の連携処理を入れればOK）
    if btn_drive:
        st.info("Google ドライブ連携はまだ実装していません。")
    if btn_web:
        st.info("Web サイト連携はまだ実装していません。")
    if btn_yt:
        st.info("YouTube 連携はまだ実装していません。")

    return st.session_state.selected_uploads


def selected_sources_ui():
    st.markdown("""
        <div style="font-size:14px; font-weight:600; margin-top:20px margin-bottom:8px;">
            選択したソース
        </div>
    """, unsafe_allow_html=True)

    if "selected_uploads" not in st.session_state:
        st.session_state.selected_uploads = []
    if "uploader_version" not in st.session_state:
        st.session_state.uploader_version = 0

    if len(st.session_state.selected_uploads) == 0:
        st.markdown("""
            <div style="
                background:#eef4ff;
                padding:20px;
                border-radius:12px;
                font-size:18px;
                color:#334;
            ">
                まだソースが追加されていません
            </div>
        """, unsafe_allow_html=True)
        return

    for i, item in enumerate(st.session_state.selected_uploads):
        f = item["file"]
        name = item["name"]
        size_mb = len(f.getvalue()) / 1024 / 1024

        col_left, col_right = st.columns([7, 1])

        with col_left:
            st.markdown(f"""
                <div style="
                    display:flex;
                    align-items:center;
                    gap:12px;
                ">
                    <span style="font-size:26px;">📄</span>
                    <div>
                        <div style="font-size:16px; font-weight:600;">{name}</div>
                        <div style="font-size:13px; opacity:0.7;">{size_mb:.1f} MB</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col_right:
            if st.button("✕", key=f"del_{i}"):
                # state から削除
                st.session_state.selected_uploads.pop(i)
                # ★ uploader をリセット（内部の選択を全部クリア）
                st.session_state.uploader_version += 1
                st.rerun()

def page_create():
    fixed_header("職人作成")
    # ─────────────────────
    # 1行目：ラベルだけを横に並べる
    # ─────────────────────
    label_col, _ = st.columns([5, 1])
    with label_col:
        # Streamlit のラベル風のスタイルで自前表示
        st.markdown(
            '<div style="font-size:14px; font-weight:600; margin-bottom:4px;">職人 名</div>',
            unsafe_allow_html=True,
        )

    # ─────────────────────
    # 2行目：左に text_input、右に作成ボタン
    # ─────────────────────
    title_col, btn_col = st.columns([5, 1])

    with title_col:
        # ラベルは上で表示しているので隠す
        title = st.text_input("", key="nb_title", label_visibility="collapsed")

    with btn_col:
        create_clicked = st.button("作成", key="create_btn", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────
    # 以下は今まで通り
    # ─────────────────────
    col_left, col_right = st.columns([1, 2])

    with col_left:
        selected_sources_ui()

    with col_right:
        upload_ui()

    st.markdown("<br><br>", unsafe_allow_html=True)

    if create_clicked:
        if not title:
            st.error("職人 名を入力してください")
            return

        nb_id = str(uuid.uuid4())
        now = datetime.now().isoformat(timespec="seconds")
        cur.execute(
            "INSERT INTO notebooks (id, title, created_at) VALUES (?,?,?)",
            (nb_id, title, now)
        )
        conn.commit()

        folder = f"data/notebooks/{nb_id}"
        os.makedirs(folder, exist_ok=True)

        for item in st.session_state.selected_uploads:
            f = item["file"]
            path = os.path.join(folder, f.name)
            with open(path, "wb") as fp:
                fp.write(f.getbuffer())
            cur.execute(
                "INSERT INTO files (id, notebook_id, filename, filepath) VALUES (?,?,?,?)",
                (str(uuid.uuid4()), nb_id, f.name, path)
            )

        conn.commit()
        st.success("職人 が作成されました！")
        st.session_state.selected_uploads.clear()
        st.query_params.update({"page": "home"})
        st.rerun()


def page_chat_welcome(nb_id):
    # -----------------------------------------------------
    # 左上ロゴとタイトル
    # -----------------------------------------------------
    nb_id = st.session_state.current_nb

    # Notebook タイトル取得
    cur.execute("SELECT title FROM notebooks WHERE id=?", (nb_id,))
    row = cur.fetchone()
    if not row:
        st.error("職人 が存在しません")
        return
    title = row[0]
    fixed_header(title)


    # ------------------------------
    # タイトル（上）
    # ------------------------------
    st.markdown("""
        <div style="text-align:center; padding-top:80px;">
            <div style="font-size:54px; font-weight:bold; margin-bottom:40px;">
                ✨ こんにちは
            </div>
        </div>
    """, unsafe_allow_html=True)


    # ----------------------------------------------------
    # ★ chat_input を「間」に固定配置（absolute 版）
    # ----------------------------------------------------
    st.markdown("""
        <style>

        /* chat_input を消す footer */
        footer {visibility: hidden;}

        /* 「間」に固定配置する */
        div[data-testid="stChatInput"] {
            position: absolute !important;
            top: -350px !important;       /* ← ★ ここで上下位置を調整 */
            left: 50% !important;
            transform: translateX(-50%);
            width: 80%;
            max-width: 900px;
            z-index: 9999;
            visibility: visible !important;
        }

        /* 見た目を調整 */
        div[data-testid="stChatInput"] input {
            border-radius: 9999px !important;
            border: 2px solid #ff7777 !important;
            background: #f3f4f7 !important;
            padding: 18px 24px !important;
            font-size: 18px !important;
        }

        </style>
    """, unsafe_allow_html=True)


    # ------------------------------
    # 本物の chat_input
    # ------------------------------
    prompt = st.chat_input("質問を入力", key="welcome_chat_input")


    # ------------------------------
    # 下の説明文
    # ------------------------------
    st.markdown("""
        <div style="text-align:center; font-size:30px; opacity:0.92; margin-top:220px;">
            ここで職人に質問を始めましょう
        </div>
    """, unsafe_allow_html=True)


    # ------------------------------
    # 入力処理
    # ------------------------------
    if prompt:
        cur.execute("""
            INSERT INTO chat_messages(id, notebook_id, role, content)
            VALUES (?, ?, ?, ?)
        """, (str(uuid.uuid4()), nb_id, "user", prompt))
        conn.commit()

        reply = f"『{prompt}』についての回答です。"
        cur.execute("""
            INSERT INTO chat_messages(id, notebook_id, role, content)
            VALUES (?, ?, ?, ?)
        """, (str(uuid.uuid4()), nb_id, "assistant", reply))
        conn.commit()

        # ★ ここで notebooks.created_at を「最後のアクティビティ時刻」として更新
        now = datetime.now().isoformat(timespec="seconds")
        cur.execute(
            "UPDATE notebooks SET created_at = ? WHERE id = ?",
            (now, nb_id)
        )
        conn.commit()

        st.query_params.update({"page": "chat", "nb": nb_id})
        st.rerun()


def page_chat_main(nb_id):
    # -----------------------------------------------------
    # 左上ロゴとタイトル
    # -----------------------------------------------------
    nb_id = st.session_state.current_nb

    # Notebook タイトル取得
    cur.execute("SELECT title FROM notebooks WHERE id=?", (nb_id,))
    row = cur.fetchone()
    if not row:
        st.error("職人 が存在しません")
        return
    title = row[0]
    fixed_header(title)

    # -----------------------------------------------------
    # 履歴表示
    # -----------------------------------------------------
    cur.execute("""
        SELECT role, content FROM chat_messages
        WHERE notebook_id=? ORDER BY created_at
    """, (nb_id,))
    msgs = cur.fetchall()

    for role, msg in msgs:
        st.chat_message(role).write(msg)

    # 本物の chat_input（これが最強）
    prompt = st.chat_input("質問を入力", key="chat_main_input")

    if prompt:
        cur.execute("""
            INSERT INTO chat_messages(id, notebook_id, role, content)
            VALUES (?, ?, ?, ?)
        """, (str(uuid.uuid4()), nb_id, "user", prompt))
        conn.commit()

        reply = f"『{prompt}』についての回答です。"
        cur.execute("""
            INSERT INTO chat_messages(id, notebook_id, role, content)
            VALUES (?, ?, ?, ?)
        """, (str(uuid.uuid4()), nb_id, "assistant", reply))
        conn.commit()

        # ★ ここでも更新
        now = datetime.now().isoformat(timespec="seconds")
        cur.execute(
            "UPDATE notebooks SET created_at = ? WHERE id = ?",
            (now, nb_id)
        )
        conn.commit()

        st.rerun()

# -----------------------------------------------------
# Router
# -----------------------------------------------------
if st.session_state.page == "home":
    page_home()
elif st.session_state.page == "create":
    page_create()
elif st.session_state.page == "chat":
    nb_id = st.session_state.current_nb

    # 履歴がない場合 → welcome 画面
    cur.execute("SELECT COUNT(*) FROM chat_messages WHERE notebook_id=?", (nb_id,))
    count = cur.fetchone()[0]

    if count == 0:
        page_chat_welcome(nb_id)
    else:
        page_chat_main(nb_id)
