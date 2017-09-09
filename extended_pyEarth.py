import sys
import pyproj, shapefile, shapely.geometry
import xlrd
from inspect import stack
from math import sin, radians
from OpenGL.GL import *
from OpenGL.GLU import *
from os.path import abspath, dirname, join, pardir
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
        self.shapefile = 'C:\\Users\\minto\\Desktop\\pyGISS\\shapefiles\\World countries.shp'
        self.nodes, self.links = {}, {}

    def initializeGL(self):
        glMatrixMode(GL_PROJECTION)
        self.create_polygons()
        
        glFrustum(-1.0, 1.0, -1.0, 1.0, 5.0, 60.0)

    def paintGL(self):
        glEnable(GL_DEPTH_TEST)
        self.quad = gluNewQuadric()
        glColor(0, 0, 255)
        self.sphere = gluSphere(self.quad, 6378137/1000000 - 0.025, 100, 100)
        
        glPushMatrix()
        glRotated(self.rx/16, 1, 0, 0)
        glRotated(self.ry/16, 0, 1, 0)
        glRotated(self.rz/16, 0, 0, 1)
        if hasattr(self, 'polygons'):
            glCallList(self.polygons)
        if hasattr(self, 'objects'):
            glCallList(self.objects)
        
        # self.create_nodes()
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
        
    def generate_objects(self):
        self.objects = glGenLists(1)
        glNewList(self.objects, GL_COMPILE)
        for node in self.nodes.values():
            glPushMatrix()
            node.ccef = self.LLH_to_ECEF(node.latitude, node.longitude, 70000)
            glTranslatef(*node.ccef)
            node = gluNewQuadric()
            gluQuadricNormals(node, GLU_SMOOTH)
            glColor(255, 255, 0)
            glEnable(GL_DEPTH_TEST)
            gluSphere(node, 0.05, 100, 100)
            glPopMatrix()
        for link in self.links.values():
            glColor(255, 0, 0)
            glBegin(GL_LINES)
            glVertex3f(*link.source.ccef)
            glVertex3f(*link.destination.ccef)
            glEnd()
        glEndList()
        
    def create_link(self, source, destination):
        glColor(255, 0, 0)
        # x1, y1, z1 = self.LLH_to_ECEF(source.latitude, source.longitude, 70000)
        # x2, y2, z2 = self.LLH_to_ECEF(destination.latitude, destination.longitude, 70000)
        glBegin(GL_LINES)
        glVertex3f(*source.ccef)
        glVertex3f(*destination.ccef)
        glEnd()
        
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
        
class Node():
    
    def __init__(self, controller, **kwargs):
        self.__dict__.update(kwargs)
        controller.view.nodes[self.name] = self
        
class Link():
    
    def __init__(self, controller, **kwargs):
        self.__dict__.update(kwargs)
        self.source = controller.view.nodes[kwargs['source']]
        self.destination = controller.view.nodes[kwargs['destination']]
        controller.view.links[self.name] = self

class PyEarth(QMainWindow):
    def __init__(self, path_app):        
        super().__init__()
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # paths
        self.path_shapefiles = join(path_app, pardir, 'shapefiles')
        self.path_projects = join(path_app, pardir, 'projects')
        
        # menu
        menu_bar = self.menuBar()
        import_shapefile = QAction('Import shapefile', self)
        import_shapefile.triggered.connect(self.import_shapefile)
        import_project = QAction('Import project', self)
        import_project.triggered.connect(self.import_project)
        menu_bar.addAction(import_shapefile)
        menu_bar.addAction(import_project)
        
        # 3D OpenGL view
        self.view = View()
        self.view.setFocusPolicy(Qt.StrongFocus)
        
        layout = QGridLayout(central_widget)
        layout.addWidget(self.view, 0, 0)
                
    def import_shapefile(self):
        self.view.shapefile = QFileDialog.getOpenFileName(self, 'Import')[0]
        self.view.create_polygons()
        
    def import_project(self):
        filepath = QFileDialog.getOpenFileName(
                                            self, 
                                            'Import project', 
                                            self.path_projects
                                            )[0]
        book = xlrd.open_workbook(filepath)
        
        # import nodes
        nodes_sheet = book.sheet_by_name('nodes')
        properties = nodes_sheet.row_values(0)
        for row_index in range(1, nodes_sheet.nrows):
            Node(self, **dict(zip(properties, nodes_sheet.row_values(row_index))))
        self.view.generate_objects()
        
        # import links
        nodes_sheet = book.sheet_by_name('links')
        properties = nodes_sheet.row_values(0)
        for row_index in range(1, nodes_sheet.nrows):
            Link(self, **dict(zip(properties, nodes_sheet.row_values(row_index))))
        self.view.generate_objects()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    path_app = dirname(abspath(stack()[0][1]))
    window = PyEarth(path_app)
    window.setWindowTitle('pyEarth: a lightweight 3D visualization of the earth')
    window.setFixedSize(900, 900)
    window.show()
    sys.exit(app.exec_())    
