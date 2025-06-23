from flask import Blueprint, request, jsonify
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()
import os
from models import (
    create_remote_connection,
    load_course,
    load_mod_rq,
    load_course_prices,
    load_course_groups
)
from google.ads.googleads.client import GoogleAdsClient
from utils.google_ads import get_ad_groups_cost

stats_bp = Blueprint("stats", __name__)

@stats_bp.route("/", methods=["GET"])
def stats():
    try:
        # Fechas
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")

        if not start_date_str:
            start_date = datetime.now() - timedelta(days=15)
        else:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")

        if not end_date_str:
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

        # Conexión y carga de datos
        remote_engine = create_remote_connection()
        df_cursos = load_course(remote_engine)
        df_leads = load_mod_rq(remote_engine)
        df_precios = load_course_prices(remote_engine)
        df_grupos = load_course_groups(remote_engine)

        df_leads["fecha_alta"] = pd.to_datetime(df_leads["fecha_alta"])
        df_leads["fecha_cierre"] = pd.to_datetime(df_leads["fecha_cierre"])
        df_precios["modification_date"] = pd.to_datetime(df_precios["modification_date"])

        # Segmentar leads por estado y fecha
        df_pendientes = df_leads[
            (df_leads["estado"] == "PENDIENTE") &
            (df_leads["fecha_alta"] >= start_date) &
            (df_leads["fecha_alta"] <= end_date)
        ]
        df_rechazadas = df_leads[
            (df_leads["estado"] == "RECHAZADA") &
            (df_leads["fecha_cierre"] >= start_date) &
            (df_leads["fecha_cierre"] <= end_date)
        ]
        df_cerradas = df_leads[
            (df_leads["estado"] == "CERRADO") &
            (df_leads["fecha_cierre"] >= start_date) &
            (df_leads["fecha_cierre"] <= end_date)
        ]

        # Google Ads
        try:
            from google.ads.googleads.client import GoogleAdsClient as AdsClient

            credentials = {
                "developer_token": os.getenv("GOOGLE_DEVELOPER_TOKEN"),
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
                "login_customer_id": os.getenv("GOOGLE_LOGIN_CUSTOMER_ID"),
                "use_proto_plus": True
            }

            googleads_client = AdsClient.load_from_dict(credentials, version="v18")
            df_ads = get_ad_groups_cost(
            googleads_client, "3454277823",
            start_date_str, end_date_str
        )

        except Exception as ads_error:
            print("⚠️ Error Google Ads:", ads_error)
            df_ads = pd.DataFrame(columns=["Ad Group ID", "Cost (in currency units)"])

        # Costo por curso
        df_grupos["Id_grupo"] = df_grupos["Id_grupo"].str.split(", ")
        df_grupos = df_grupos.explode("Id_grupo")
        df_grupos["Id_grupo"] = df_grupos["Id_grupo"].astype(str)
        df_ads["Ad Group ID"] = df_ads["Ad Group ID"].astype(str)

        df_ads_cost = pd.merge(
            df_grupos,
            df_ads,
            left_on="Id_grupo",
            right_on="Ad Group ID",
            how="left"
        )
        df_ads_cost["Cost (in currency units)"] = df_ads_cost["Cost (in currency units)"].fillna(0)
        df_ads_cost = df_ads_cost.groupby("idCurso")["Cost (in currency units)"].sum().reset_index()
        df_ads_cost.rename(columns={"idCurso": "Id_course", "Cost (in currency units)": "costoAds"}, inplace=True)

        # Conteos por curso
        counts = df_cursos[["Id_course", "NombreCurso"]].copy()
        counts["CERRADO"] = counts["Id_course"].map(df_cerradas["idCurso"].value_counts()).fillna(0).astype(int)
        counts["PENDIENTE"] = counts["Id_course"].map(df_pendientes["idCurso"].value_counts()).fillna(0).astype(int)
        counts["RECHAZADA"] = counts["Id_course"].map(df_rechazadas["idCurso"].value_counts()).fillna(0).astype(int)

        # Precio promedio ponderado
        def calc_precio_promedio(id_curso):
            precios = df_precios[
                (df_precios["course_id"] == id_curso) &
                (df_precios["modification_date"] <= end_date)
            ].sort_values("modification_date")

            if precios.empty:
                return 0

            total_ventas = 0
            total_ingresos = 0
            prev_precio = 0
            prev_fecha = start_date

            for _, row in precios.iterrows():
                ventas = df_cerradas[
                    (df_cerradas["idCurso"] == id_curso) &
                    (df_cerradas["fecha_cierre"] >= prev_fecha) &
                    (df_cerradas["fecha_cierre"] < row["modification_date"])
                ].shape[0]
                total_ventas += ventas
                total_ingresos += ventas * prev_precio
                prev_precio = row["price"]
                prev_fecha = row["modification_date"]

            ventas = df_cerradas[
                (df_cerradas["idCurso"] == id_curso) &
                (df_cerradas["fecha_cierre"] >= prev_fecha) &
                (df_cerradas["fecha_cierre"] <= end_date)
            ].shape[0]
            total_ventas += ventas
            total_ingresos += ventas * prev_precio

            return round(total_ingresos / total_ventas, 2) if total_ventas > 0 else 0

        counts["Precio_promedio"] = counts["Id_course"].apply(calc_precio_promedio)

        # Costo por lead
        counts = pd.merge(counts, df_ads_cost, on="Id_course", how="left")
        counts["costoAds"] = counts["costoAds"].fillna(0)
        total_leads = counts["CERRADO"] + counts["PENDIENTE"] + counts["RECHAZADA"]
        counts["Costo_por_Lead"] = (counts["costoAds"] / total_leads.replace(0, 1)).round(2)

        # Tasa de venta
        counts["Tasa_de_venta"] = (
            counts["CERRADO"] * 100 / (counts["PENDIENTE"] + counts["RECHAZADA"]).replace(0, 1)
        ).round(2)

        # ROI
        counts['Precio_promedio'] = counts['Precio_promedio'].replace({pd.NA: 0}).fillna(0)
        counts['Tasa_de_venta'] = counts['Tasa_de_venta'].replace({pd.NA: 0}).fillna(0)

        # Evitar división por cero
        denominador = ((counts['Precio_promedio'] / 100) * counts['Tasa_de_venta']).replace(0, 1)

        counts['ROI'] = 1 - (
            0.19 + 0.07 + 0.21 + 0.16 +
            (counts['Costo_por_Lead'] / denominador)
        )

        counts['ROI'] = counts['ROI'].round(2).fillna(0)


        return jsonify(counts.to_dict(orient="records"))

    except Exception as e:
        return jsonify({"error": str(e)}), 500
