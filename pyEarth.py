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

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import QtOpenGL
from math import *
import pyproj, shapefile, shapely.geometry
from OpenGL.GL import *
from OpenGL.GLU import *



class GLWidget(QtOpenGL.QGLWidget):
    
    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)
        self.x_rotation = 0
        self.y_rotation = 0
        self.z_rotation = 0
        self.gear1Rot = 0
        
        # Number of latitudes in sphere
        self.lats = 100

        # Number of longitudes in sphere
        self.longs = 100
        
        self.shapefile = 'C:\\Users\\minto\\Desktop\\pyGISS\\shapefiles\\World countries.shp'

        timer = QTimer(self)
        timer.timeout.connect(self.advanceGears)
        timer.start(20)

    def initializeGL(self):
        self.polygons = self.create_polygons()

        glEnable(GL_NORMALIZE)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glPushMatrix()
        glRotated(self.x_rotation / 16.0, 1.0, 0.0, 0.0)
        glRotated(self.y_rotation / 16.0, 0.0, 1.0, 0.0)
        glRotated(self.z_rotation / 16.0, 0.0, 0.0, 1.0)
        
        quad = gluNewQuadric()
        gluQuadricNormals(quad, GLU_SMOOTH)
        glColor(0, 0, 255)
        glEnable(GL_DEPTH_TEST)
        gluSphere(quad, 6378137/1000000 - 0.1, 100, 100)
        glColor(0, 0, 0)
        # glFlush()

        self.drawGear(self.polygons, 0.0, 0.0, 0.0, self.gear1Rot / 50.0)

        glPopMatrix()

    def resizeGL(self, w, h):
        side = min(w, h)
        glViewport(0, 0, side*2, side*2)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glFrustum(-1.0, +1.0, -1.0, 1.0, 5.0, 60.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslated(0.0, 0.0, -40.0)
        
    def mousePressEvent(self, event):
        self.lastPos = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.x() - self.lastPos.x()
        dy = event.y() - self.lastPos.y()

        if event.buttons() and Qt.LeftButton:
            self.x_rotation += 8 * dy
            self.y_rotation += 8 * dx
        elif event.buttons() and Qt.RightButton:
            self.x_rotation += 8 * dy
            self.z_rotation += 8 * dx

        self.lastPos = event.pos()

    def advanceGears(self):
        self.gear1Rot += 2 * 8
        self.updateGL()    
        
    def create_polygons(self):
        list = glGenLists(1)
        glNewList(list, GL_COMPILE)
        # glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, reflectance)
        
        for polygon in self.draw_polygons():
            glColor(0, 255, 0)
            glBegin(GL_LINE_STRIP)
            for point in polygon + [polygon[0]]:
                lon, lat = point
                x, y, z = self.pyproj_LLH_to_ECEF(lat, lon, 1)
                factor = 1000000
                x, y, z = x/factor, y/factor, z/factor
                glVertex3f(x, y, z)
            glEnd()

        glEndList()

        return list
        
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

    def drawGear(self, gear, dx, dy, dz, angle):
        glPushMatrix()
        glTranslated(dx, dy, dz)
        glRotated(angle, 0.0, 0.0, 1.0)
        glCallList(gear)
        glPopMatrix()

class MainWindow(QMainWindow):
    def __init__(self):        
        super(MainWindow, self).__init__()

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        self.glWidget = GLWidget()
        self.pixmapLabel = QLabel()

        self.glWidgetArea = GLWidget()
        
        centralLayout = QGridLayout()
        centralLayout.addWidget(self.glWidgetArea, 0, 0)
        centralWidget.setLayout(centralLayout)

        self.setWindowTitle('pyEarth')
        self.resize(400, 300)

    def createSlider(self, changedSignal, setterSlot):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 360 * 16)
        slider.setSingleStep(16)
        slider.setPageStep(15 * 16)
        slider.setTickInterval(15 * 16)
        slider.setTickPosition(QSlider.TicksRight)

        slider.valueChanged.connect(setterSlot)
        changedSignal.connect(slider.setValue)

        return slider




if __name__ == '__main__':

    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())    
