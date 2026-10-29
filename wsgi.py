"""Entrada WSGI de produccion: gunicorn wsgi:app."""
from app import create_app

app = create_app()
