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

class View():
    
    def __init__(self):
        self.x, self.y, self.z = 0, 0, 50
        self.cx, self.cy, self.cz = 0, 0, -1
        self.ux, self.uy, self.uz = 0, 1, 0
        
    def render(self):
        return (self.x, self.y, self.z, self.cx, self.cy, self.cz, self.ux, self.uy, self.uz)
    
class GLWidget(QOpenGLWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_rotation = 0
        self.y_rotation = 0
        self.z_rotation = 0
        self.gear1Rot = 0
        
        # Number of latitudes in sphere
        self.lats = 100

        # Number of longitudes in sphere
        self.longs = 100
        
        self.view = View()
        
        self.factor = 1
        
        self.shapefile = 'C:\\Users\\minto\\Desktop\\pyGISS\\shapefiles\\World countries.shp'
    
        timer = QTimer(self)
        timer.timeout.connect(self.advanceGears)
        timer.start(20)

    def initializeGL(self):
        self.create_polygons()

        glEnable(GL_NORMALIZE)

    def move(self):
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glRotatef(self.view.pitch, 1, 0, 0)
        glRotatef(self.view.yaw, 0, 1, 0)
        glRotatef(self.view.roll, 0, 0, 1)
        glTranslatef(self.view.x, self.view.y, self.view.z)
        glCallList(self.polygons)
        
    def paintGL(self):
        glColor(255, 255, 255, 0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # glPushMatrix()
        # glRotated(self.x_rotation / 16.0, 1.0, 0.0, 0.0)
        # glRotated(self.y_rotation / 16.0, 0.0, 1.0, 0.0)
        # glRotated(self.z_rotation / 16.0, 0.0, 0.0, 1.0)
        
        # self.move()
        self.quad = gluNewQuadric()
        # glScalef(self.factor, self.factor, self.factor)
        gluQuadricNormals(self.quad, GLU_SMOOTH)
        glColor(0, 0, 255)
        glEnable(GL_DEPTH_TEST)
        self.sphere = gluSphere(self.quad, 6378137/1000000 - 0.025, 100, 100)
        glColor(0, 0, 0)
        # self.drawGear(0.0, 0.0, 0.0, self.gear1Rot / 50.0)
        glCallList(self.polygons)
        # glPopMatrix()
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(*self.view.render())
        
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
        
    def triangulate(polygon, holes=[]):
        """
        Returns a list of triangles.
        Uses the GLU Tesselator functions!
        """
        vertices = []
        def edgeFlagCallback(param1, param2): pass
        def beginCallback(param=None):
            vertices = []
        def vertexCallback(vertex, otherData=None):
            vertices.append(vertex[:2])
        def combineCallback(vertex, neighbors, neighborWeights, out=None):
            out = vertex
            return out
        def endCallback(data=None): pass
    
        tess = gluNewTess()
        gluTessProperty(tess, GLU_TESS_WINDING_RULE, GLU_TESS_WINDING_ODD)
        gluTessCallback(tess, GLU_TESS_EDGE_FLAG_DATA, edgeFlagCallback)#forces triangulation of polygons (i.e. GL_TRIANGLES) rather than returning triangle fans or strips
        gluTessCallback(tess, GLU_TESS_BEGIN, beginCallback)
        gluTessCallback(tess, GLU_TESS_VERTEX, vertexCallback)
        gluTessCallback(tess, GLU_TESS_COMBINE, combineCallback)
        gluTessCallback(tess, GLU_TESS_END, endCallback)
        gluTessBeginPolygon(tess, 0)
    
        #first handle the main polygon
        gluTessBeginContour(tess)
        for point in polygon:
            point3d = (point[0], point[1], point[2])
            gluTessVertex(tess, point3d, point3d)
        gluTessEndContour(tess)
    
        #then handle each of the holes, if applicable
        if holes != []:
            for hole in holes:
                gluTessBeginContour(tess)
                for point in hole:
                    point3d = (point[0], point[1], point[2])
                    gluTessVertex(tess, point3d, point3d)
                gluTessEndContour(tess)
    
        gluTessEndPolygon(tess)
        gluDeleteTess(tess)
        return vertices

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
        self.view.z += 1*(-1 if delta > 0 else 1)

    def mouseMoveEvent(self, event):
        dx = event.x() - self.last_position.x()
        dy = event.y() - self.last_position.y()
        
        self.view.cx -= dx/50
        self.view.cy += dy/50

        if event.buttons() and Qt.LeftButton:
            self.x_rotation += 8 * dy
            self.y_rotation += 8 * dx
        elif event.buttons() and Qt.RightButton:
            self.x_rotation += 8 * dy
            self.z_rotation += 8 * dx

        self.last_position = event.pos()

    def advanceGears(self):
        self.gear1Rot += 2 * 8
        self.update()    
        

        
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

class MainWindow(QMainWindow):
    def __init__(self):        
        super(MainWindow, self).__init__()

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        self.glWidgetArea = GLWidget()
        
        centralLayout = QGridLayout()
        centralLayout.addWidget(self.glWidgetArea, 0, 0)
        centralWidget.setLayout(centralLayout)

        self.setWindowTitle('pyEarth')
        self.resize(400, 300)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())    
