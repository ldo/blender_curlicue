#+
# This addon for Blender 2.7 generates a tapering spiral-shaped mesh.
#
# Copyright 2015-2020 Lawrence D'Oliveiro <ldo@geek-central.gen.nz>.
# Licensed under CC-BY-SA <http://creativecommons.org/licenses/by-sa/4.0/>.
#-

import math
import sys # debug
import os
import bpy
import mathutils
from mathutils import \
    Matrix, \
    Vector
from bpy_extras import \
    object_utils

bl_info = \
    {
        "name" : "Curlicue",
        "author" : "Lawrence D'Oliveiro <ldo@geek-central.gen.nz>",
        "version" : (0, 2, 2),
        "blender" : (2, 83, 0),
        "location" : "Add > Mesh > Curlicue",
        "description" :
            "creates a tapering spiral mesh.",
        "warning" : "",
        "wiki_url" : "",
        "tracker_url" : "",
        "category" : "Add Mesh",
    }

class Failure(Exception) :

    def __init__(self, msg) :
        self.msg = msg
    #end __init__

#end Failure

def props_compat(cllass) :
    "converts property definitions from pre-2.8 form to 2.8+ form."
    prop_funcs = set \
      (
        getattr(bpy.props, propname)
        for propname in dir(bpy.props)
        if propname.endswith("Property") and propname != "RemoveProperty"
      )
    props = list \
      (
        (name, prop)
        for name in dir(cllass)
        for prop in (getattr(cllass, name),)
        if isinstance(prop, tuple) and len(prop) == 2 and prop[0] in prop_funcs
      )
    for prop in props :
        delattr(cllass, prop[0])
    #end for
    if not hasattr(cllass, "__annotations__") :
        cllass.__annotations__ = {}
    #end if
    cllass.__annotations__.update(dict(props))
    return cllass
#end props_compat

@props_compat
class Curlicue(bpy.types.Operator) :
    bl_idname = "mesh.curlicue"
    bl_label = "Curlicue"
    bl_context = "objectmode"
    bl_options = {"REGISTER", "UNDO"}

    curve_type = bpy.props.EnumProperty \
      (
        name = "Type",
        description = "the type of spiral curve",
        items =
            (
                ("linear", "Linear", "linear spiral"),
                ("log", "Logarithmic", "logarithmic spiral"),
            ),
        default = "linear",
      )
    nr_points = bpy.props.IntProperty \
      (
        name = "Points",
        description = "how many points to place along the length of the spiral",
        min = 1,
        default = 32,
      )
    nr_turns = bpy.props.FloatProperty \
      (
        name = "Turns",
        description = "how many turns the spiral will make",
        default = 1.0,
      )
    radius = bpy.props.FloatProperty \
      (
        name = "Radius",
        description = "how large to make the spiral",
        min = 0.1,
        default = 1.0,
      )
    inner_taper = bpy.props.FloatProperty \
      (
        name = "Inner Taper",
        description = "the width of the innermost end of the spiral",
        min = 0,
        default = 0.1,
      )
    outer_taper = bpy.props.FloatProperty \
      (
        name = "Outer Taper",
        description = "the width of the outermost end of the spiral",
        min = 0,
        default = 0.0,
      )
    linear_offset = bpy.props.FloatProperty \
      (
        name = "Linear Offset",
        description = "the starting radius of the innermost end of the spiral (linear only)",
        min = 0,
        default = 0.0,
      )
    radius_ratio = bpy.props.FloatProperty \
      (
        name = "Radius Ratio",
        description = "the ratio of the radii of successive full turns (logarithmic only)",
        min = 0,
        default = 1.0,
      )

    def draw(self, context) :
        the_col = self.layout.column(align = True)
        #the_col.label("Curlicue:") # Blender already labels redo panel for me
        the_col.prop(self, "curve_type")
        the_col.prop(self, "nr_points")
        the_col.prop(self, "nr_turns")
        the_col.prop(self, "radius")
        the_col.prop(self, "inner_taper")
        the_col.prop(self, "outer_taper")
        the_col.prop(self, "linear_offset")
        the_col.prop(self, "radius_ratio")
    #end draw

    def action_common(self, context, redoing) :
        try :
            curve_name = "Curlicue"
            vertices = []
            faces = []
            for i in range(self.nr_points) :
                angle = i / self.nr_points * self.nr_turns * 2 * math.pi
                if self.curve_type == "linear" :
                    radius = \
                        (
                            i / self.nr_points * (self.radius - self.linear_offset)
                        +
                            self.linear_offset
                        )
                elif self.curve_type == "log" :
                    radius = \
                        (
                            self.radius
                        *
                            self.radius_ratio ** (angle / (2 * math.pi) - self.nr_turns)
                        )
                else :
                    raise Failure("SHOULDN’T OCCUR: unrecognized curve type")
                #end if
                width = \
                    (
                        self.outer_taper * i / self.nr_points
                    +
                        self.inner_taper * (1 - i / self.nr_points)
                    )
                to_midpoint = \
                    (
                        Matrix.Rotation(angle, 4, "Z")
                    @
                        Matrix.Translation(Vector((radius, 0, 0)))
                    )
                orient = math.pi / 2 # !
                pt1 = \
                    (
                        to_midpoint
                    @
                        Matrix.Rotation(orient + math.pi / 2, 4, "Z")
                    @
                        Matrix.Translation(Vector((width / 2, 0, 0)))
                    @
                        Vector((0, 0, 0))
                    )
                pt2 = \
                    (
                        to_midpoint
                    @
                        Matrix.Rotation(orient - math.pi / 2, 4, "Z")
                    @
                        Matrix.Translation(Vector((width / 2, 0, 0)))
                    @
                        Vector((0, 0, 0))
                    )
                vertices.extend([pt1, pt2])
                if len(vertices) >= 4 :
                    faces.append(list(len(vertices) + i for i in (-4, -3, -1, -2)))
                #end if
            #end for
            the_curve = bpy.data.meshes.new(curve_name)
            the_curve.from_pydata(vertices, [], faces)
            object_utils.object_data_add(context, the_curve, name = curve_name)
            # all done
            status = {"FINISHED"}
        except Failure as why :
            sys.stderr.write("Failure: {}\n".format(why.msg)) # debug
            self.report({"ERROR"}, why.msg)
            status = {"CANCELLED"}
        #end try
        return \
            status
    #end action_common

    def execute(self, context) :
        return \
            self.action_common(context, True)
    #end execute

    def invoke(self, context, event) :
        return \
            self.action_common(context, False)
    #end invoke

#end Curlicue

def add_invoke_item(self, context) :
    self.layout.operator(Curlicue.bl_idname)
#end add_invoke_item

def register() :
    bpy.utils.register_class(Curlicue)
    bpy.types.VIEW3D_MT_mesh_add.append(add_invoke_item)
#end register

def unregister() :
    bpy.utils.unregister_class(Curlicue)
    bpy.types.VIEW3D_MT_mesh_add.remove(add_invoke_item)
#end unregister

if __name__ == "__main__" :
    register()
#end if
