# Introduction

pyEarth is a lightweight 3D visualization of the Earth implemented with pyQt and OpenGL.
Users can import shapefiles to visualize maps in 3D, create objects (nodes or links) using Excel, and 
export a project to Google Earth.

![pyEarth demo](https://github.com/afourmy/PyEarth/blob/master/readme/pyEarth.gif)

# pyEarth versions

## Standard version (pyEarth.py, < 150 lines)

The standard version implements pyEarth in less than 150 lines of code.
Maps can be created by importing shapefiles, and the following bindings are implemented:
* the scroll wheel for zooming in and out.
* the left-click button rotates the earth in any direction
* the right-click button moves the view in the 3-dimensional space (like a viewfinder)
* pressing space will start a continuous rotation of the earth

A few shapefiles are available for testing in the 'pyEarth/shapefiles' folder (world countries, continents, US).

## Extended version (extended_pyEarth.py, < 300 lines)

In the extended version, besides the import of shapefiles, nodes and links can be created on the map by importing an Excel file (an example is available in the 'PyGISS/projects' folder).
A pyEarth project can then be exported to Google Earth (a KML file is created).

# How it works

A point on the earth is defined as a longitude and a latitude.
Longitude and latitude are angles.

![pyEarth](https://github.com/afourmy/pyEarth/blob/master/readme/how_it_works_0.png)

We need to convert a point defined with geodetic coordinates ('Latitude, Longitude, Height', or LLH system) to a point defined with carthesian coordinates ('x, y, z', or ECEF system, "Earth-Centered, Earth-Fixed", also known as ECR ("Earth-Centered Rotational").

![pyEarth](https://github.com/afourmy/pyEarth/blob/master/readme/how_it_works_1.png)

To convert geodetic coordinates to carthesian coordinates, we use a library called pyproj.

![pyEarth](https://github.com/afourmy/pyEarth/blob/master/readme/how_it_works_2.png)

In order to create a 3D space, we use pyQt and python interface to OpenGL: pyOpenGL.
pyQt has a special widget for OpenGL support, QOpenGLWidget.
We use this widget along with pyOpenGL function to create the 3D objects and implement a freefly camera.

![pyEarth](https://github.com/afourmy/pyEarth/blob/master/readme/how_it_works_3.png)

To draw the polygons, we need their coordinates.
A shapefile (.shp) is a file that describes vector data as a set of shapes. For a map, there are two types of shapes: polygons and multipolygons.
Polygons and multipolygons are defined as a set of points (longitude, latitude) on the earth.

![pyEarth](https://github.com/afourmy/pyEarth/blob/master/readme/how_it_works_4.png)

To read the shapefile and extract the shapes it contains, we will use the pyshp library.
Once this is done, we have a set of shapes, polygons and mutipolygons.

![pyEarth](https://github.com/afourmy/pyEarth/blob/master/readme/how_it_works_5.png)

We can draw polygons with the GUI framework polygon function. A multipolygon is actually composed of multiple polygons.
To draw a multipolygon, we will decompose it into the polygons it is made of with the shapely library.

![pyEarth](https://github.com/afourmy/pyEarth/blob/master/readme/how_it_works_6.png)

The resulting algorithm is:

``` 
- Use pyshp to read the shapefile
- Extract the shapes of the shapefile
- When a shape is a multipolygon, decompose it into multiple polygons with shapely
- Use pyproj to convert the shape's geodetic coordinates to carthesian coordinates
- Triangulate the polygon with the tesselation function
- Use OpenGL functions to create the polygon in the 3D space
``` 

Below is the algorithm implemented with the pyQt framework:

```python
# function to convert coordinates from LLH to ECEF with pyproj
def LLH_to_ECEF(self, lat, lon, alt):
    ecef, llh = pyproj.Proj(proj='geocent'), pyproj.Proj(proj='latlong')
    x, y, z = pyproj.transform(llh, ecef, lon, lat, alt, radians=False)
    return x, y, z
    
# function to extract the polygons (shapefile library) and convert multipolygons 
# into polygons when necessary (shapely library)
def extract_polygons(self):
    if not hasattr(self, 'shapefile'):
        return
    sf = shapefile.Reader(self.shapefile)       
    polygons = sf.shapes() 
    for polygon in polygons:
        polygon = shapely.geometry.shape(polygon)
        yield from [polygon] if polygon.geom_type == 'Polygon' else polygon
      
# function that performs the tesselation process (polygon triangulation): 
# polygons are broken down into triangles
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
    
# finally, we extract the polygons, triangulate them, and use OpenGL functions
# to create the triangles in the 3D space
def create_polygons(self):
    self.polygons = glGenLists(1)
    glNewList(self.polygons, GL_COMPILE)
    for polygon in self.extract_polygons():
        glColor(0, 255, 0)
        glBegin(GL_TRIANGLES)
        for vertex in self.polygon_tesselator(polygon):
            glVertex(*vertex)
        glEnd()
    glEndList()
```

# Contact

You can contact me at my personal email address:
```
''.join(map(chr, (97, 110, 116, 111, 105, 110, 101, 46, 102, 111, 
117, 114, 109, 121, 64, 103, 109, 97, 105, 108, 46, 99, 111, 109)))
```

or on the [Network to Code slack](http://networktocode.herokuapp.com "Network to Code slack"). (@minto)

# pyEarth dependencies

pyQt5 is required: it can be download from the [Riverband website](https://www.riverbankcomputing.com/software/pyqt/download5)

PyEarth relies on three Python libraries:

* pyshp, used for reading shapefiles.
* shapely, used for converting a multipolygon into a set of polygons
* pyproj, used for translating geographic coordinates (longitude and latitude) into projected coordinates

Before using pyEarth, you must make sure all these libraries are properly installed:

```
pip install pyshp
pip install shapely
pip install pyproj
```

# Credits

[OpenGL](https://www.opengl.org): 2D and 3D graphics application programming interface.

[pyshp](https://github.com/GeospatialPython/pyshp): A library to read and write ESRI Shapefiles.

[shapely](https://github.com/Toblerity/Shapely): A library for the manipulation and analysis of geometric objects in the Cartesian plane.

[pyproj](https://github.com/jswhit/pyproj): Python interface to PROJ4 library for cartographic transformations
