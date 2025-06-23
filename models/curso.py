from db import db

class CursoStats(db.Model):
    __tablename__ = 'curso_stats'  # Reemplazá con tu tabla real
    id = db.Column(db.Integer, primary_key=True)
    curso = db.Column(db.String(255))
    ventas = db.Column(db.Integer)
    pendientes = db.Column(db.Integer)
    rechazados = db.Column(db.Integer)
    precio = db.Column(db.Float)
    costo_ads = db.Column(db.Float)
    costo_por_lead = db.Column(db.Float)
    fecha_ultima_venta = db.Column(db.Date)
