"""Exporta las ventas a CSV ANONIMIZADO para análisis o para compartir.

- Se eliminan vendedor_id, cliente_id e id de venta.
- La fecha se generaliza a año-mes.
- Se agrupa por mes + categoría + talla y se suprimen los grupos con menos
  de K ventas (k-anonimato), que podrían señalar a una persona.

Uso:
    python -m scripts.exportar_anonimo ventas_anonimas.csv
"""
import csv
import sys
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

from app.anonimizacion import K_MINIMO, generalizar_fecha  # noqa: E402
from app.database import conectar  # noqa: E402


def filas_anonimas(con) -> list[dict]:
    grupos = defaultdict(lambda: {"ventas": 0, "unidades": 0, "monto": 0})
    for f in con.execute(
        """SELECT v.fecha, p.categoria, p.talla, v.cantidad, v.precio_unitario
           FROM ventas v JOIN productos p ON p.id = v.producto_id"""
    ):
        g = grupos[(generalizar_fecha(f["fecha"]), f["categoria"], f["talla"])]
        g["ventas"] += 1
        g["unidades"] += f["cantidad"]
        g["monto"] += f["cantidad"] * f["precio_unitario"]
    return [
        {"mes": mes, "categoria": cat, "talla": talla, **v}
        for (mes, cat, talla), v in sorted(grupos.items())
        if v["ventas"] >= K_MINIMO
    ]


def main(destino: str) -> None:
    con = conectar()
    filas = filas_anonimas(con)
    con.close()
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["mes", "categoria", "talla",
                                          "ventas", "unidades", "monto"])
        w.writeheader()
        w.writerows(filas)
    print(f"{len(filas)} grupos exportados a {destino}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ventas_anonimas.csv")
