import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Modelo Macro BTC", page_icon="₿", layout="wide")
st.title("₿ Modelo Macro Bitcoin — S2F + M2 + Adoção")
st.markdown("Ajusta os parâmetros e vê a projeção atualizar em tempo real.")

# ── SLIDERS (sidebar) ──────────────────────────────────────
st.sidebar.header("⚙️ Parâmetros do Modelo")

P0              = st.sidebar.number_input("Preço atual BTC ($)", 10000, 500000, 85000, 1000)
anos_proj       = st.sidebar.slider("Horizonte (anos)", 1, 15, 8)
M2_growth_anual = st.sidebar.slider("Crescimento M2 anual (%)", 1, 20, 7) / 100
M2_elasticity   = st.sidebar.slider("Elasticidade BTC ao M2", 0.3, 1.5, 0.8, 0.05)
adoption_base   = st.sidebar.slider("Adoção atual (%)", 1, 15, 5) / 100
adoption_max    = st.sidebar.slider("Teto adoção (%)", 10, 60, 25) / 100
adoption_speed  = st.sidebar.slider("Velocidade adoção", 0.1, 1.0, 0.35, 0.05)
metcalfe_exp    = st.sidebar.slider("Expoente Metcalfe", 1.0, 2.0, 1.7, 0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("Pesos do Modelo")
w_s2f      = st.sidebar.slider("Peso S2F", 0.1, 0.8, 0.35, 0.05)
w_m2       = st.sidebar.slider("Peso M2",  0.1, 0.8, 0.35, 0.05)
w_adoption = round(1 - w_s2f - w_m2, 2)
st.sidebar.info(f"Peso Adoção (automático): {w_adoption:.2f}")

# ── MOTOR ──────────────────────────────────────────────────
ano_base = 2026
anos     = np.arange(0, anos_proj + 1)
t_abs    = ano_base + anos

def get_reward(y):
    if y < 2028:   return 3.125
    elif y < 2032: return 1.5625
    else:          return 0.78125

def get_supply(y):
    s = 19.72e6
    for yr in range(ano_base, y):
        s += get_reward(yr) * 144 * 365
    return min(s, 21e6)

sf_vals    = np.array([get_supply(y)/(get_reward(y)*144*365) for y in t_abs])
s2f_factor = (sf_vals / sf_vals[0]) ** 0.4

M2_base   = 108e12
M2_series = M2_base * (1 + M2_growth_anual) ** anos
m2_factor = (M2_series / M2_base) ** M2_elasticity

t0              = 5
adoption_t      = adoption_base + (adoption_max - adoption_base) / \
                  (1 + np.exp(-adoption_speed * (anos - t0)))
adoption_factor = (adoption_t / adoption_base) ** metcalfe_exp

composite  = (s2f_factor**w_s2f) * (m2_factor**w_m2) * (adoption_factor**w_adoption)
price_base = P0 * composite

cf_bear    = (s2f_factor**w_s2f) * \
             ((M2_base*(1.03**anos)/M2_base)**M2_elasticity)**w_m2 * \
             (((adoption_base+(adoption_max*0.5-adoption_base)/(1+np.exp(-0.2*(anos-t0))))/adoption_base)**metcalfe_exp)**w_adoption
price_bear = P0 * cf_bear * 0.85

cf_bull    = (s2f_factor**w_s2f) * \
             ((M2_base*(1.12**anos)/M2_base)**M2_elasticity)**w_m2 * \
             (((adoption_base+(adoption_max-adoption_base)/(1+np.exp(-0.55*(anos-t0))))/adoption_base)**metcalfe_exp)**w_adoption
price_bull = P0 * cf_bull * 1.20

# ── MÉTRICAS ───────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("🐻 Bear (final)", f"${price_bear[-1]/1e3:.0f}k",
            f"{(price_bear[-1]/P0-1)*100:.0f}% vs hoje")
col2.metric("📊 Base (final)", f"${price_base[-1]/1e3:.0f}k",
            f"{(price_base[-1]/P0-1)*100:.0f}% vs hoje")
col3.metric("🐂 Bull (final)", f"${price_bull[-1]/1e3:.0f}k",
            f"{(price_bull[-1]/P0-1)*100:.0f}% vs hoje")

# ── GRÁFICO ────────────────────────────────────────────────
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=list(t_abs)+list(t_abs[::-1]),
    y=list(price_bull)+list(price_bear[::-1]),
    fill='toself', fillcolor='rgba(99,179,237,0.12)',
    line=dict(color='rgba(0,0,0,0)'), name='Intervalo'))
fig.add_trace(go.Scatter(x=t_abs, y=price_bear, mode='lines+markers',
    line=dict(color='red', width=2, dash='dot'), name='Bear'))
fig.add_trace(go.Scatter(x=t_abs, y=price_base, mode='lines+markers',
    line=dict(color='orange', width=3), name='Base'))
fig.add_trace(go.Scatter(x=t_abs, y=price_bull, mode='lines+markers',
    line=dict(color='green', width=2, dash='dot'), name='Bull'))
for h in [y for y in t_abs if y in [2028, 2032]]:
    fig.add_vline(x=h, line_dash='dash', line_color='gray',
                  annotation_text=f"Halving {h}", annotation_position='top right')
fig.update_layout(yaxis_type='log', xaxis_title='Ano',
                  yaxis_title='Preço BTC ($)', height=500)
st.plotly_chart(fig, use_container_width=True)

# ── TABELA ─────────────────────────────────────────────────
import pandas as pd
df = pd.DataFrame({
    "Ano": t_abs,
    "S2F": sf_vals.round(1),
    "M2 ($T)": (M2_series/1e12).round(1),
    "Adoção (%)": (adoption_t*100).round(1),
    "Bear ($k)": (price_bear/1e3).round(0).astype(int),
    "Base ($k)": (price_base/1e3).round(0).astype(int),
    "Bull ($k)": (price_bull/1e3).round(0).astype(int),
})
st.dataframe(df, use_container_width=True, hide_index=True)
