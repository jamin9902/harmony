import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps

"""
Uses parts of CS50: Finance

http://cdn.cs50.net/2020/fall/psets/9/finance/finance.zip
"""

def guide(message, redirect):
    """Render guide message and redirect user"""
    
    return render_template("guide.html", message=message, redirect=redirect)
    

def error(message, code=400):
    """Render error message for user"""
    
    return render_template("error.html", message=message, code=code), code


def login_required(f):
    """
    Decorate routes to require login

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
