import sys
from inspect import stack
from os.path import abspath, dirname

# prevent python from writing *.pyc files / __pycache__ folders
sys.dont_write_bytecode = True

path_app = dirname(abspath(stack()[0][1]))

if path_app not in sys.path:
    sys.path.append(path_app)

import sys
import math
from math import sin, radians

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import QtOpenGL
from math import *
import pyproj, shapefile, shapely.geometry
from OpenGL.GL import *
from OpenGL.GLU import *

class Camera():
    
    def __init__(self):
        self.x, self.y, self.z = 0, 0, 50
        self.cx, self.cy, self.cz = 0, 0, -1
        self.ux, self.uy, self.uz = 0, 1, 0
        
    def render(self):
        return (self.x, self.y, self.z, self.cx, self.cy, self.cz, self.ux, self.uy, self.uz)
    
class View(QOpenGLWidget):
    
    def __init__(self, path_app, parent=None):
        super().__init__(parent)
        self.path_app = path_app
        self.x_rotation = 0
        self.y_rotation = 0
        self.z_rotation = 0
        self.gear1Rot = 0
        
        # Number of latitudes in sphere
        self.lats = 100

        # Number of longitudes in sphere
        self.longs = 100
        
        self.camera = Camera()
        
        self.factor = 1
        
        self.shapefile = 'C:\\Users\\minto\\Desktop\\pyGISS\\shapefiles\\World countries.shp'
    
        timer = QTimer(self)
        timer.timeout.connect(self.advanceGears)
        timer.start(20)

    def initializeGL(self):
        self.create_polygons()
        self.create_node(28, 47)
        glEnable(GL_NORMALIZE)
        
    def paintGL(self):
        glColor(255, 255, 255, 0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        self.quad = gluNewQuadric()
        gluQuadricNormals(self.quad, GLU_SMOOTH)
        glColor(0, 0, 255)
        
        self.sphere = gluSphere(self.quad, 6378137/1000000 - 0.025, 100, 100)

        glColor(0, 255, 0)
        glPushMatrix()
        # glRotated(self.x_rotation / 16.0, 1.0, 0.0, 0.0)
        # glRotated(self.y_rotation / 16.0, 0.0, 1.0, 0.0)
        # glRotated(self.z_rotation / 16.0, 0.0, 0.0, 1.0)
        glCallList(self.polygons)
        glPopMatrix()
        

        self.create_node(28, 47)
        self.create_node(2, 48)
        self.create_link(28, 47, 2, 48)
        
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(*self.camera.render())
        
    def create_link(self, lon1, lat1, lon2, lat2):
        glColor(255, 0, 0)
        x1, y1, z1 = self.pyproj_LLH_to_ECEF(lat1, lon1, 70000)
        x2, y2, z2 = self.pyproj_LLH_to_ECEF(lat2, lon2, 70000)
        factor = 1000000
        x1, y1, z1 = x1/factor, y1/factor, z1/factor
        x2, y2, z2 = x2/factor, y2/factor, z2/factor
        glBegin(GL_LINES)
        glVertex3f(x1, y1, z1)
        glVertex3f(x2, y2, z2)
        glEnd()
        
    def create_node(self, longitude, latitude):
        glPushMatrix()
        x, y, z = self.pyproj_LLH_to_ECEF(latitude, longitude, 70000)
        factor = 1000000
        x, y, z = x/factor, y/factor, z/factor
        glTranslatef(x, y, z)
        node = gluNewQuadric()
        gluQuadricNormals(node, GLU_SMOOTH)
        glColor(255, 255, 0)
        glEnable(GL_DEPTH_TEST)
        self.node = gluSphere(node, 0.05, 100, 100)
        glPopMatrix()

    def resizeGL(self, w, h):
        side = min(w, h)
        glViewport(w//4, -20, side, side)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glFrustum(-1.0, 1.0, -1.0, 1.0, 5.0, 60.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslated(0.0, 0.0, -40.0)
        
    def mousePressEvent(self, event):
        glPushMatrix()
        glScalef(2, 2, 2)
        glCallList(self.polygons)
        glPopMatrix()
        self.last_position = event.pos()
        a = self.mapFromGlobal(self.last_position)
        print(a.x(), a.y())
        
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.camera.z += 1*(-1 if delta > 0 else 1)

    def mouseMoveEvent(self, event):
        dx = event.x() - self.last_position.x()
        dy = event.y() - self.last_position.y()
        
        self.camera.cx -= dx/50
        self.camera.cy += dy/50

        if event.buttons() and Qt.LeftButton:
            self.x_rotation += 8 * dy
            self.y_rotation += 8 * dx
        elif event.buttons() and Qt.RightButton:
            self.x_rotation += 8 * dy
            self.z_rotation += 8 * dx

        self.last_position = event.pos()

    def advanceGears(self):
        self.x_rotation += 8
        self.y_rotation += 8
        self.update()    
        
    def create_polygons(self):
        self.polygons = glGenLists(1)
        glNewList(self.polygons, GL_COMPILE)
        
        for polygon in self.draw_polygons():
            glColor(0, 255, 0)
            glLineWidth(2)
            glBegin(GL_LINE_LOOP)
            for point in polygon:
                lon, lat = point
                x, y, z = self.pyproj_LLH_to_ECEF(lat, lon, 1)
                factor = 1000000
                x, y, z = x/factor, y/factor, z/factor
                glVertex3f(x, y, z)

            glEnd()
        glEndList()
        

        
    def draw_polygons(self):
        sf = shapefile.Reader(self.shapefile)       
        polygons = sf.shapes() 
        for polygon in polygons:
            polygon = shapely.geometry.shape(polygon)
            if polygon.geom_type == 'Polygon':
                polygon = [polygon]
            for land in polygon:
                land = str(land)[10:-2].replace(', ', ',').replace(' ', ',')
                coords = land.replace('(', '').replace(')', '').split(',')
                yield [coords for coords in zip(coords[0::2], coords[1::2])]
        
    def LLHtoECEF(self, lat, lon, alt):
        # see http://www.mathworks.de/help/toolbox/aeroblks/llatoecefposition.html
        import numpy as np
        rad = np.float64(6378137.0)        # Radius of the Earth (in meters)
        f = np.float64(1.0/298.257223563)  # Flattening factor WGS84 Model
        np.cosLat = np.cos(lat)
        np.sinLat = np.sin(lat)
        FF     = (1.0-f)**2
        C      = 1/np.sqrt(np.cosLat**2 + FF * np.sinLat**2)
        S      = C * FF
    
        x = (rad * C + alt)*np.cosLat * np.cos(lon)
        y = (rad * C + alt)*np.cosLat * np.sin(lon)
        z = (rad * S + alt)*np.sinLat
        return x, y, z
        
    def pyproj_LLH_to_ECEF(self, lat, lon, alt):
        ecef = pyproj.Proj(proj='geocent', ellps='WGS84', datum='WGS84')
        lla = pyproj.Proj(proj='latlong', ellps='WGS84', datum='WGS84')    
        x, y, z = pyproj.transform(lla, ecef, lon, lat, alt, radians=False)
        return x, y, z

class PyEarth(QMainWindow):
    def __init__(self, path_app):        
        super().__init__()
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        menu_bar = self.menuBar()
        import_shapefile = QAction('Import shapefile', self)
        import_shapefile.triggered.connect(self.import_shapefile)
        menu_bar.addAction(import_shapefile)
        self.view = View(path_app)
        layout = QGridLayout(central_widget)
        layout.addWidget(self.view, 0, 0)
                
    def import_shapefile(self):
        self.view.shapefile = QFileDialog.getOpenFileName(self, 'Import')[0]
        self.view.redraw_map()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PyEarth(path_app)
    window.setWindowTitle('pyGISS: a lightweight GIS software')
    window.setGeometry(100, 100, 900, 900)
    window.show()
    sys.exit(app.exec_())    
