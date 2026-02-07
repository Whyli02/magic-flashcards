import streamlit as st
import pandas as pd
import os
import asyncio
import edge_tts
import tempfile
import base64
import time
from openai import OpenAI

# --- 1. 迪士尼主题 CSS 注入 (强化手机端兼容) ---
def inject_disney_css():
    st.markdown("""
    <style>
    /* 全局背景：星空渐变感 */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* 统一所有文字的字体族，确保手机端显示一致 */
    html, body, [class*="st-"] {
        font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji" !important;
    }

    /* 标题美化 */
    h1, h2, h3 {
        text-align: center;
        font-weight: 800 !important;
    }

    /* 魔法卡片：金色发光大圆角 */
    .stCard {
        background-color: white;
        border-radius: 35px !important;
        box-shadow: 0 15px 35px rgba(0,0,0,0.1) !important;
        border: 5px solid #FFD700 !important;
        margin-bottom: 20px;
        transition: transform 0.3s ease;
    }

    /* 重点：统一正反面字体大小和样式控制 */
    .word-main {
        font-size: 70px !important; /* 手机端 70px 比较稳妥，不至于撑破行 */
        color: #1E88E5;
        font-weight: 800;
        margin: 0;
        line-height: 1.2;
    }
    .phonetic-sub {
        font-size: 28px;
        color: #666;
        margin-top: 10px;
    }
    .meaning-main {
        font-size: 42px !important;
        color: #D32F2F;
        font-weight: 800;
        margin-bottom: 15px;
    }
    .collocation-sub {
        font-size: 22px;
        color: #558B2F;
        line-height: 1.5;
        padding: 0 10px;
    }

    /* 按钮美化：胶囊形状 */
    .stButton>button {
        border-radius: 25px !important;
        border: none !important;
        font-weight: bold !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
    }
    
    /* 隐藏顶部导航 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心语音函数 ---
async def get_voice_b64(text):
    if not text: return None
    voice = "zh-CN-XiaoxiaoNeural" 
    try:
        comm = edge_tts.Communicate(text, voice, rate="+10%")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t:
            await comm.save(t.name)
            with open(t.name, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except:
        return None

def load_any_file(path):
    if not os.path.exists(path): return pd.DataFrame()
    try:
        if path.endswith('.xlsx'): return pd.read_excel(path)
        return pd.read_csv(path, encoding='utf-8-sig')
    except:
        try: return pd.read_csv(path, encoding='gbk')
        except: return pd.DataFrame()

# --- 3. 初始化配置 ---
st.set_page_config(page_title="Magic English", layout="centered")
inject_disney_css()
TECH_LINK = "技术服务电话：13813811381"

if 'user_logged_in' not in st.session_state:
    st.session_state.update({
        'user_logged_in': False, 'curr_user_name': None, 
        'api_key_val': "", 'card_idx': 0, 'is_flipped': False,
        'audio_b64': None, 'audio_key': 0
    })

# --- 4. 登录界面 ---
if not st.session_state.user_logged_in:
    st.markdown("<h1 style='color: #1E3A8A; margin-top:50px;'>✨ 魔法英语森林 🔐</h1>", unsafe_allow_html=True)
    xlsx_files = [f for f in os.listdir('.') if f.endswith('.xlsx') and not f.startswith('~$')]
    
    if not xlsx_files:
        st.info("👋 请将学生名单 (.xlsx) 放入文件夹~")
    else:
        file_choice = st.selectbox("🏰 选择你的班级", xlsx_files)
        df_n = load_any_file(file_choice)
        
        if not df_n.empty and df_n.shape[1] >= 2:
            with st.form("login_form"):
                user_list = df_n.iloc[:, 0].dropna().astype(str).tolist()
                sel_user = st.selectbox("👤 你的名字", user_list)
                sel_pwd = st.text_input("🔑 魔法口令", type="password")
                if st.form_submit_button("开启魔法门", use_container_width=True):
                    user_data = df_n[df_n.iloc[:, 0].astype(str) == sel_user]
                    if not user_data.empty and str(sel_pwd) == str(user_data.iloc[0, 1]):
                        st.session_state.update({'user_logged_in': True, 'curr_user_name': sel_user})
                        st.rerun()
                    else: st.error("👻 密码不对哦！")
    
    st.markdown(f"<div style='text-align:center; color:#999; margin-top:50px;'>🪄 {TECH_LINK}</div>", unsafe_allow_html=True)
    st.stop()

# --- 5. 单词学习主界面 ---
df_w = load_any_file("words.csv")
if not df_w.empty:
    total_count = len(df_w)
    st.session_state.card_idx %= total_count
    row_data = df_w.iloc[st.session_state.card_idx]
    
    word_text = str(row_data.iloc[0]).strip()
    phonetic_text = str(row_data.iloc[1]).strip() if len(row_data) > 1 else ""
    meaning_part = str(row_data.iloc[2]).strip() if len(row_data) > 2 else ""
    collocation_part = " ".join([str(x).strip() for x in row_data.iloc[3:].dropna()]) if len(row_data) > 3 else ""

    st.markdown(f"<p style='text-align:center; color:#555;'>🌟 魔法进度: {st.session_state.card_idx + 1} / {total_count}</p>", unsafe_allow_html=True)
    st.progress((st.session_state.card_idx + 1) / total_count)

    # --- 卡片渲染 (字体统一优化) ---
    st.markdown('<div class="stCard">', unsafe_allow_html=True)
    if not st.session_state.is_flipped:
        st.markdown(f"""
            <div style='text-align:center; padding: 60px 20px;'>
                <p class='word-main'>{word_text}</p>
                <p class='phonetic-sub'>[{phonetic_text}]</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style='text-align:center; padding: 50px 20px; background-color:#FFF9E6; border-radius:30px;'>
                <p class='meaning-main'>{meaning_part}</p>
                <hr style='border: 1px dashed #FFD700;'>
                <p class='collocation-sub'>✨ {collocation_part}</p>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 按钮区 ---
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        if st.button("⬅️ 上一个"):
            st.session_state.update({'card_idx': st.session_state.card_idx - 1, 'is_flipped': False, 'audio_b64': None})
            st.rerun()
    with c2:
        if st.button("🔄 变变变"):
            st.session_state.update({'is_flipped': not st.session_state.is_flipped, 'audio_b64': None})
            st.rerun()
    with c3:
        if st.button("🔊 听听看", type="primary"):
            target_text = f"{meaning_part}。搭配用法：{collocation_part}" if st.session_state.is_flipped else word_text
            st.session_state.audio_b64 = asyncio.run(get_voice_b64(target_text))
            st.session_state.audio_key = time.time()
            st.rerun()
    with c4:
        if st.button("下一个 ➡️"):
            st.session_state.update({'card_idx': st.session_state.card_idx + 1, 'is_flipped': False, 'audio_b64': None})
            st.rerun()

    # 音频播放
    if st.session_state.audio_b64:
        st.markdown(f'<div style="display:none;"><audio autoplay key="{st.session_state.audio_key}"><source src="data:audio/mp3;base64,{st.session_state.audio_b64}"></audio></div>', unsafe_allow_html=True)

    # AI 解析
    with st.expander("🧙‍♂️ 魔法师深度解析"):
        api_key = st.text_input("DeepSeek Key", value=st.session_state.api_key_val, type="password")
        st.session_state.api_key_val = api_key
        if st.button("请教魔法师"):
            if api_key:
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"详细解析单词 {word_text}"}])
                st.success(resp.choices[0].message.content)

    # 底部退出
    st.divider()
    col_ex1, col_ex2, col_ex3 = st.columns([1, 2, 1])
    with col_ex2:
        if st.button("🏰 退出城堡，换人登录", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    st.markdown(f"<div style='text-align:center; color:#999; font-size:14px; margin-top:20px; border-top:1px dashed #ccc; padding-top:10px;'>🪄 {TECH_LINK}</div>", unsafe_allow_html=True)
else:
    st.error("⚠️ 咒语书丢失了！")