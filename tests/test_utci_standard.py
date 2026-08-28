"""
test_utci_standard.py

Test diagnostico del calcolo UTCI.

Scopo:
    Verificare esclusivamente il calcolo UTCI di pythermalcomfort,
    senza:
      - attività / MET
      - v_relative()
      - solar_gain()
      - calcolo della radiazione
      - stima della MRT

Usiamo direttamente:
    Ta  = temperatura dell'aria
    RH  = umidità relativa
    v   = velocità del vento
    MRT = temperatura radiante media

Punto di riferimento:
    Firenze, 10 giugno 2026, ore 12:00 circa

Dati ERA5:
    Ta  = 26.36 °C
    RH  = 40.43 %
    wind = 4.75 m/s

MRT:
    vengono provati diversi valori, compreso il valore
    fornito dal dataset Copernicus UTCI (~50.24 °C).

IMPORTANTE:
    In questo test la velocità del vento viene passata
    direttamente a utci(). Non viene applicato v_relative().
"""

from pythermalcomfort.models import utci


# ================================================================
# DATI AMBIENTALI
# ================================================================

TA = 26.36       # °C
RH = 40.43       # %
WIND = 4.75      # m/s


# ================================================================
# VALORI MRT DA TESTARE
# ================================================================

MRT_VALUES = [
    TA,       # condizione di riferimento: MRT = Ta
    40.00,
    50.24,    # valore Copernicus circa alle 12
    60.00,
    70.00,
    85.27,    # valore prodotto dal nostro modello precedente
]


# ================================================================
# CALCOLO
# ================================================================

print()
print("=" * 70)
print("TEST UTCI STANDARD")
print("=" * 70)

print()
print("Condizioni ambientali:")
print(f"  Ta    = {TA:.2f} °C")
print(f"  RH    = {RH:.2f} %")
print(f"  vento = {WIND:.2f} m/s")

print()
print("NOTA:")
print("  vento passato direttamente a utci()")
print("  nessun v_relative()")
print("  nessun MET")
print("  nessun solar_gain()")
print()


print("-" * 70)
print(f"{'MRT [°C]':>12} {'UTCI [°C]':>15}")
print("-" * 70)


results = []

for mrt in MRT_VALUES:

    result = utci(
        tdb=[TA],
        tr=[mrt],
        v=[WIND],
        rh=[RH],
        limit_inputs=False,
        round_output=False,
    )

    utci_value = float(result.utci[0])

    results.append((mrt, utci_value))

    print(f"{mrt:12.2f} {utci_value:15.3f}")


print("-" * 70)


# ================================================================
# CONFRONTO PARTICOLARE CON MRT COPERNICUS
# ================================================================

mrt_copernicus = 50.24

result = utci(
    tdb=[TA],
    tr=[mrt_copernicus],
    v=[WIND],
    rh=[RH],
    limit_inputs=False,
    round_output=False,
)

utci_copernicus_mrt = float(result.utci[0])


print()
print("=" * 70)
print("CASO MRT COPERNICUS")
print("=" * 70)

print(f"Ta             = {TA:.2f} °C")
print(f"RH             = {RH:.2f} %")
print(f"vento          = {WIND:.2f} m/s")
print(f"MRT Copernicus = {mrt_copernicus:.2f} °C")
print(f"UTCI calcolato = {utci_copernicus_mrt:.3f} °C")

print()
print("Questo valore è quello da confrontare con l'UTCI")
print("fornito dal dataset derived-utci-historical-timeseries.")
print()


# ================================================================
# CONFRONTO CON IL VENTO RELATIVO
# ================================================================

print("=" * 70)
print("CONTROLLO: EFFETTO DI v_relative()")
print("=" * 70)

try:

    from pythermalcomfort.utilities import v_relative

    # Valore usato nel vecchio programma:
    # walking = 1.7 met
    MET = 1.7

    vr = float(
        v_relative(
            v=[WIND],
            met=MET,
        )[0]
    )

    result_vr = utci(
        tdb=[TA],
        tr=[mrt_copernicus],
        v=[vr],
        rh=[RH],
        limit_inputs=False,
        round_output=False,
    )

    utci_vr = float(result_vr.utci[0])

    print()
    print(f"vento ERA5       = {WIND:.3f} m/s")
    print(f"MET              = {MET:.2f}")
    print(f"v_relative       = {vr:.3f} m/s")
    print(f"UTCI con vento ERA5      = {utci_copernicus_mrt:.3f} °C")
    print(f"UTCI con v_relative      = {utci_vr:.3f} °C")
    print()
    print(
        f"Differenza = {utci_vr - utci_copernicus_mrt:+.3f} °C"
    )

except Exception as e:

    print()
    print("Impossibile eseguire il test v_relative():")
    print(e)


print()
print("=" * 70)
print("FINE TEST")
print("=" * 70)
print()
