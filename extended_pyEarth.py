import pyproj
import shapefile
import shapely.geometry
import sys
import warnings
from inspect import stack
from math import cos, pi, sin
from OpenGL.GL import *
from OpenGL.GLU import *
from os.path import abspath, dirname, join, pardir
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import *
try:
    import simplekml
except ImportError:
    warnings.warn('simplekml not installed: export to google earth disabled')
try:
    import xlrd
except ImportError:
    warnings.warn('xlrd not installed: import of project disabled')
    
class View(QOpenGLWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        for coord in ('x', 'y', 'z', 'cx', 'cy', 'cz', 'rx', 'ry', 'rz'):
            setattr(self, coord, 50 if coord == 'z' else 0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.nodes, self.links = {}, {}

    def initializeGL(self):
        glMatrixMode(GL_PROJECTION)
        self.create_polygons()
        glFrustum(-1, 1, -1, 1, 5, 1000)

    def paintGL(self):
        glColor(0, 0, 255)
        glEnable(GL_DEPTH_TEST)
        glBegin(GL_POLYGON)
        for vertex in range(0, 100):
            angle, radius = float(vertex)*2.0*pi/100, 6378137/1000000
            glVertex3f(cos(angle)*radius, sin(angle)*radius, 0.0)
        glEnd()
        
        glPushMatrix()
        glRotated(self.rx/16, 1, 0, 0)
        glRotated(self.ry/16, 0, 1, 0)
        glRotated(self.rz/16, 0, 0, 1)
        if hasattr(self, 'polygons'):
            glCallList(self.polygons)
        if hasattr(self, 'objects'):
            glCallList(self.objects)
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
        self.rx, self.ry = self.rx + 36, self.ry + 36
        
    def generate_objects(self):
        self.objects = glGenLists(1)
        glNewList(self.objects, GL_COMPILE)
        for node in self.nodes.values():
            glPushMatrix()
            node.ccef = self.LLH_to_ECEF(node.latitude, node.longitude, 70000)
            glTranslatef(*node.ccef)
            node = gluNewQuadric()
            gluQuadricNormals(node, GLU_SMOOTH)
            glColor(0, 0, 0)
            glEnable(GL_DEPTH_TEST)
            gluSphere(node, 0.02, 100, 100)
            glPopMatrix()
        for link in self.links.values():
            glColor(255, 0, 0)
            glBegin(GL_LINES)
            glVertex3f(*link.source.ccef)
            glVertex3f(*link.destination.ccef)
            glEnd()
        glEndList()
                
    def create_polygons(self):
        self.polygons = glGenLists(1)
        glNewList(self.polygons, GL_COMPILE)
        for polygon in self.draw_polygons():
            glLineWidth(2)
            glBegin(GL_LINE_LOOP)
            glColor(0, 0, 0)
            for lon, lat in polygon.exterior.coords:
                glVertex3f(*self.LLH_to_ECEF(lat, lon, 1))
            glEnd()
            glColor(0, 255, 0)
            glBegin(GL_TRIANGLES)
            for vertex in self.polygon_tesselator(polygon):
                glVertex(*vertex)
            glEnd()
        glEndList()
        
    def polygon_tesselator(self, polygon):    
        vertices, tess = [], gluNewTess()
        gluTessCallback(tess, GLU_TESS_EDGE_FLAG_DATA, lambda *args: None)
        gluTessCallback(tess, GLU_TESS_VERTEX, lambda v: vertices.append(v))
        gluTessCallback(tess, GLU_TESS_COMBINE, lambda v, *args: v)
        gluTessCallback(tess, GLU_TESS_END, lambda: None)
        
        gluTessBeginPolygon(tess, 0)
        gluTessBeginContour(tess)
        for lon, lat in polygon.exterior.coords:
            point = self.LLH_to_ECEF(lat, lon, 0)
            gluTessVertex(tess, point, point)
        gluTessEndContour(tess)
        gluTessEndPolygon(tess)
        gluDeleteTess(tess)
        return vertices
        
    def draw_polygons(self):
        if not hasattr(self, 'shapefile'):
            return
        sf = shapefile.Reader(self.shapefile)       
        polygons = sf.shapes() 
        for polygon in polygons:
            polygon = shapely.geometry.shape(polygon)
            yield from [polygon] if polygon.geom_type == 'Polygon' else polygon
        
    def LLH_to_ECEF(self, lat, lon, alt):
        ecef, llh = pyproj.Proj(proj='geocent'), pyproj.Proj(proj='latlong')
        x, y, z = pyproj.transform(llh, ecef, lon, lat, alt, radians=False)
        return x/1000000, y/1000000, z/1000000
        
class Node():
    
    def __init__(self, controller, **kwargs):
        self.__dict__.update(kwargs)
        self.coords = [(float(self.longitude), float(self.latitude))]
        controller.view.nodes[self.name] = self
        
class Link():
    
    def __init__(self, controller, **kwargs):
        self.__dict__.update(kwargs)
        self.source = controller.view.nodes[kwargs['source']]
        self.destination = controller.view.nodes[kwargs['destination']]
        self.coords = [self.source.coords[0], self.destination.coords[0]]
        controller.view.links[self.name] = self
        
class GoogleEarthExport(QWidget):  

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle('Export to Google Earth')
        
        node_size = QLabel('Node label size')
        self.node_size = QLineEdit('2')
        
        path = 'https://raw.githubusercontent.com/afourmy/pyEarth/master/images/node.png'
        self.path_edit = QLineEdit(path)
        
        line_width = QLabel('Line width')
        self.line_width = QLineEdit('2')
        
        path_to_icon = QPushButton('Node icon')
        path_to_icon.clicked.connect(self.choose_path)
        
        export = QPushButton('Export to KML')
        export.clicked.connect(self.kml_export)
        
        layout = QGridLayout()
        layout.addWidget(node_size, 0, 0)
        layout.addWidget(self.node_size, 0, 1)
        layout.addWidget(self.path_edit, 1, 1)
        layout.addWidget(line_width, 2, 0)
        layout.addWidget(self.line_width, 2, 1)
        layout.addWidget(path_to_icon, 1, 0)
        layout.addWidget(export, 3, 0, 1, 2)
        self.setLayout(layout)
        
    def kml_export(self):
        kml = simplekml.Kml()
        
        point_style = simplekml.Style()
        point_style.labelstyle.color = simplekml.Color.blue
        point_style.labelstyle.scale = float(self.node_size.text())
        point_style.iconstyle.icon.href = self.path_edit.text()
        
        for node in self.controller.view.nodes.values():
            point = kml.newpoint(name=node.name, description=node.description)
            point.coords = node.coords
            point.style = point_style
            
        line_style = simplekml.Style()
        line_style.linestyle.color = simplekml.Color.red
        line_style.linestyle.width = self.line_width.text()
            
        for link in self.controller.view.links.values():
            line = kml.newlinestring(name=link.name, description=link.description) 
            line.coords = link.coords
            line.style = line_style
            
        filepath = QFileDialog.getSaveFileName(
                                               self, 
                                               'KML export', 
                                               'project', 
                                               '.kml'
                                               )
        selected_file = ''.join(filepath)
        kml.save(selected_file)
        self.close()
        
    def choose_path(self):
        path = 'Choose an icon'
        filepath = ''.join(QFileDialog.getOpenFileName(self, path, path))
        self.path_edit.setText(filepath)
        self.path = filepath

class PyEarth(QMainWindow):
    def __init__(self, path_app):        
        super().__init__()
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # paths
        self.path_shapefiles = join(path_app, pardir, 'shapefiles')
        self.path_projects = join(path_app, pardir, 'projects')
        path_icons = join(path_app, 'icons')
        
        # menu
        menu_bar = self.menuBar()
        
        import_shapefile_icon = QIcon(join(path_icons, 'globe.png'))
        import_shapefile = QAction(import_shapefile_icon, 'Import a shapefile', self)
        import_shapefile.setStatusTip('Import a shapefile')
        import_shapefile.triggered.connect(self.import_shapefile)
        
        import_project_icon = QIcon(join(path_icons, 'import_project.png'))
        import_project = QAction(import_project_icon, 'Import a Excel project', self)
        import_project.setStatusTip('Import a project (Excel format)')
        import_project.triggered.connect(self.import_project)
        
        kml_export_icon = QIcon(join(path_icons, 'kml_export.png'))
        kml_export = QAction(kml_export_icon, 'KML Export', self)
        kml_export.setStatusTip('Import current project to Google Earth (KML)')
        kml_export.triggered.connect(self.kml_export)
        
        toolbar = self.addToolBar('')
        toolbar.resize(1500, 1500)
        toolbar.setIconSize(QSize(70, 70))
        toolbar.addAction(import_shapefile)
        toolbar.addAction(import_project)
        toolbar.addAction(kml_export)
        
        # KML export window
        self.kml_export_window = GoogleEarthExport(self)
        
        # 3D OpenGL view
        self.view = View()
        self.view.setFocusPolicy(Qt.StrongFocus)
        
        layout = QGridLayout(central_widget)
        layout.addWidget(self.view, 0, 0)
                
    def import_shapefile(self):
        self.view.shapefile = QFileDialog.getOpenFileName(self, 'Import')[0]
        self.view.create_polygons()
        
    def import_project(self):
        filepath = QFileDialog.getOpenFileName(self, 'Import project', 
                                                        self.path_projects)[0]
        book = xlrd.open_workbook(filepath)
        for obj_type, obj_class in (('nodes', Node), ('links', Link)):
            sheet = book.sheet_by_name(obj_type)
            properties = sheet.row_values(0)
            for row in range(1, sheet.nrows):
                obj_class(self, **dict(zip(properties, sheet.row_values(row))))
            self.view.generate_objects()
            
    def kml_export(self):
        self.kml_export_window.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    path_app = dirname(abspath(stack()[0][1]))
    window = PyEarth(path_app)
    window.setWindowTitle('pyEarth: a lightweight 3D visualization of the earth')
    window.setFixedSize(900, 900)
    window.show()
    sys.exit(app.exec_())    
