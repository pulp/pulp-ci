# see:
# https://raw.githubusercontent.com/pulp/crane/3c657fe53020b804ce60d907a82b4fb19aebe532/deployment/crane_el6.wsgi
# for this unpleasantry is necessary.
import sys
sys.path.insert(0, '/usr/lib/python2.6/site-packages/Jinja2-2.6-py2.6.egg')

from crane.wsgi import application
