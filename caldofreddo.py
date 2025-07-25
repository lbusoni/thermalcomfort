import numpy as np

def heat_exchange(
    T_air_C,
    RH,
    v_wind,
    T_skin_C=34,
    area_body=1.8,
    vol_respiratory_Lmin=10,
):
    # Costanti fisiche
    sigma = 5.67e-8        # Stefan-Boltzmann [W/m²K⁴]
    epsilon_skin = 0.98     # emissività pelle
    L = 0.5                 # lunghezza caratteristica corpo [m]
    p_atm = 101325          # pressione atmosferica [Pa]
    R_v = 461.5             # costante specifica vapore acqueo [J/kg/K]
    L_v = 2.42e6            # calore latente evaporazione [J/kg]

    # Converti temperature in K
    T_air = T_air_C + 273.15
    T_skin = T_skin_C + 273.15
    delta_T = T_skin - T_air

    # Proprietà aria (approssimazioni a T_air)
    # Dati approssimativi interpolati per aria secca
    if T_air_C < 0:
        rho_air = 1.29
        cp_air = 1005
        mu_air = 1.7e-5
        k_air = 0.024
        Pr = 0.71
    elif T_air_C <= 35:
        rho_air = 1.2 - 0.003 * T_air_C
        cp_air = 1005 + 0.1 * T_air_C
        mu_air = 1.7e-5 + 1e-7 * T_air_C
        k_air = 0.024 + 0.0001 * T_air_C
        Pr = 0.71
    else:
        rho_air = 1.1
        cp_air = 1010
        mu_air = 2e-5
        k_air = 0.026
        Pr = 0.7

    nu_air = mu_air / rho_air  # viscosità cinematica

    # Numero di Reynolds (convezione forzata)
    Re = v_wind * L / nu_air if v_wind > 0 else 0

    # Numero di Nusselt (convezione forzata)
    if Re > 0:
        Nu_forz = 0.037 * Re**0.8 * Pr**(1/3)
    else:
        Nu_forz = 0

    # Numero di Grashof (convezione naturale)
    beta = 1 / T_air
    g = 9.81
    Gr = (g * beta * delta_T * L**3) / (nu_air**2)
    Ra = Gr * Pr

    # Numero di Nusselt (convezione naturale)
    if 1e4 < Ra < 1e9:
        Nu_nat = 0.59 * Ra**(1/4)
    else:
        # limite minimo per Nu per evitare zero o valori non fisici
        Nu_nat = 1.0

    # Calcolo coefficiente di scambio termico convettivo totale (somma conv naturale + forzata)
    h_nat = Nu_nat * k_air / L
    h_forz = Nu_forz * k_air / L
    # Generalmente la convezione totale è approssimata come somma lineare o max tra i due
    h_total = h_nat + h_forz

    # Flusso convettivo
    q_conv = h_total * delta_T  # [W/m²]

    # Flusso radiazione
    q_rad = epsilon_skin * sigma * (T_skin**4 - T_air**4)

    # Evaporazione cutanea

    def p_sat_water(T_C):
        """Pressione di saturazione vapore acqua in Pa"""
        return 610.78 * np.exp((17.27 * T_C) / (T_C + 237.3))

    p_vap_skin = p_sat_water(T_skin_C)  # pressione vapore sulla pelle (satura)
    p_vap_air = RH * 0.01 * p_sat_water(T_air_C)  # pressione vapore aria

    delta_p_vap = p_vap_skin - p_vap_air

    # coefficiente di scambio di massa (analogia a h totale)
    hm = h_total / (rho_air * cp_air)

    # densità vapore acqueo a T_skin
    rho_vap = 1 / (R_v * T_skin)

    # flusso evaporazione cutanea (massa)
    m_dot_evap = hm * delta_p_vap * rho_vap

    # flusso calore evaporazione cutanea
    q_evap_cut = m_dot_evap * L_v  # [W/m²]

    # Evaporazione respiratoria

    # Volume respirato in m³/s
    vol_resp_m3s = vol_respiratory_Lmin / 1000 / 60

    # Calore sensibile respirazione
    q_resp_sens = vol_resp_m3s * rho_air * cp_air * (T_skin - T_air)  # [W]

    # Calore latente respirazione
    p_vap_resp_air = RH * 0.01 * p_sat_water(T_air_C)
    delta_p_vap_resp = p_vap_skin - p_vap_resp_air

    m_dot_evap_resp = vol_resp_m3s * delta_p_vap_resp * rho_vap * hm  # kg/s (approssimazione)

    q_resp_lat = m_dot_evap_resp * L_v  # [W]

    q_resp_total = q_resp_sens + q_resp_lat

    # Totali su superficie corporea
    q_conv_tot = q_conv * area_body
    q_rad_tot = q_rad * area_body
    q_evap_cut_tot = q_evap_cut * area_body
    q_resp_tot = q_resp_total

    q_total = q_conv_tot + q_rad_tot + q_evap_cut_tot + q_resp_tot

    # Output dettagliato
    results = {
        "Convezione (W/m²)": q_conv,
        "Irraggiamento (W/m²)": q_rad,
        "Evaporazione cutanea (W/m²)": q_evap_cut,
        "Evaporazione respiratoria (W)": q_resp_tot,
        "Flusso totale (W)": q_total
    }

    return results

# Esempio d'uso
params = {
    "T_air_C": 0,
    "RH": 30,
    "v_wind": 1,
    "T_skin_C": 34,
    "area_body": 1.8,
    "vol_respiratory_Lmin": 10,
}

result = heat_exchange(**params)
for k, v in result.items():
    print(f"{k}: {v:.1f}")
