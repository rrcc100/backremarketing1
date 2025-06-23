import pandas as pd
from sqlalchemy import create_engine

def create_remote_connection():
    engine = create_engine("mysql+mysqlconnector://gestarCRM:Xx5TD7hFLd2rNMcx@190.15.194.218:64309/gestarcrm")
    return engine

def load_course(engine):
    query = "SELECT id AS Id_course, title AS NombreCurso, category_id FROM course"
    return pd.read_sql(query, engine)

def load_mod_rq(remote_engine):
    query = "SELECT idCurso, estado, fecha_alta, fecha_cierre, idetiqueta FROM mod_rq"
    return pd.read_sql(query, remote_engine)

def load_course_prices(engine):
    query = "SELECT course_id, price, modification_date FROM course_prices"
    return pd.read_sql(query, engine)

def load_course_groups(engine):
    query = "SELECT idCurso, Id_grupo FROM course_groups"
    return pd.read_sql(query, engine)


