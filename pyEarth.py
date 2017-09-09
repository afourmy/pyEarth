import sys
from math import sin, radians
import pyproj, shapefile, shapely.geometry
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QAction, QApplication, QFileDialog, QGridLayout, 
                                    QMainWindow, QWidget, QOpenGLWidget)
    
class View(QOpenGLWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        for coord in ('x', 'y', 'z', 'cx', 'cy', 'cz', 'rx', 'ry', 'rz'):
            setattr(self, coord, 50 if coord == 'z' else 0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)

    def initializeGL(self):
        glMatrixMode(GL_PROJECTION)
        glFrustum(-1.0, 1.0, -1.0, 1.0, 5.0, 60.0)

    def paintGL(self):
        glEnable(GL_DEPTH_TEST)
        self.quad = gluNewQuadric()
        glColor(0, 0, 255)
        self.sphere = gluSphere(self.quad, 6378137/1000000 - 0.025, 100, 100)
        
        if hasattr(self, 'polygons'):
            glPushMatrix()
            glRotated(self.rx/16, 1, 0, 0)
            glRotated(self.ry/16, 0, 1, 0)
            glRotated(self.rz/16, 0, 0, 1)
            glCallList(self.polygons)
            glPopMatrix()
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.x, self.y, self.z, self.cx, self.cy, self.cz, 0, 1, 0)
        self.update()
        
    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        
    def wheelEvent(self, event):
        self.z += -2 if event.angleDelta().y() > 0 else 2

    def mouseMoveEvent(self, event):
        dx, dy = event.x() - self.last_pos.x(), event.y() - self.last_pos.y()
        if event.buttons() == Qt.LeftButton:
            self.rx, self.ry = self.rx + 8*dy, self.ry + 8*dx
        elif event.buttons() == Qt.RightButton:
            self.cx, self.cy = self.cx - dx/50, self.cy + dy/50
        self.last_pos = event.pos()
         
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            if self.timer.isActive():
                self.timer.stop()
            else:
                self.timer.start()
            
    def rotate(self):  
        self.rx, self.ry = self.rx + 6, self.ry + 6
        
    def create_polygons(self):
        self.polygons = glGenLists(1)
        glNewList(self.polygons, GL_COMPILE)
        for polygon in self.draw_polygons():
            glColor(0, 255, 0)
            glBegin(GL_LINE_LOOP)
            for (lon, lat) in polygon:
                glVertex3f(*self.LLH_to_ECEF(lat, lon, 1))
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
                longitudes, latitudes = land.exterior.coords.xy
                yield zip(longitudes, latitudes)
        
    def LLH_to_ECEF(self, lat, lon, alt):
        ecef = pyproj.Proj(proj='geocent', ellps='WGS84', datum='WGS84')
        lla = pyproj.Proj(proj='latlong', ellps='WGS84', datum='WGS84')    
        x, y, z = pyproj.transform(lla, ecef, lon, lat, alt, radians=False)
        return x/1000000, y/1000000, z/1000000

class PyEarth(QMainWindow):
    def __init__(self):        
        super().__init__()
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        menu_bar = self.menuBar()
        import_shapefile = QAction('Import shapefile', self)
        import_shapefile.triggered.connect(self.import_shapefile)
        menu_bar.addAction(import_shapefile)
        self.view = View()
        self.view.setFocusPolicy(Qt.StrongFocus)
        layout = QGridLayout(central_widget)
        layout.addWidget(self.view, 0, 0)
                
    def import_shapefile(self):
        self.view.shapefile = QFileDialog.getOpenFileName(self, 'Import')[0]
        self.view.create_polygons()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PyEarth()
    window.setWindowTitle('pyEarth: a lightweight 3D visualization of the earth')
    window.setFixedSize(900, 900)
    window.show()
    sys.exit(app.exec_())    
