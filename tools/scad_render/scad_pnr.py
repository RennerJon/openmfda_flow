import math
import operator
import solid
import solid.utils
import sys
import os
import shutil
import numpy as np
import pandas as pd
try:
    import odb
except ImportError:
    import opendbpy as odb
from functools import reduce
class Params():
    def __init__(self, db):
        self.route_params = None
        self.db = db

    """
    This sets the pixel size scale unique to the printer.
    All x,y dimensions are scalar multiples of the "px" value and
    z dimensions are scalar multiples of the "layer" value. For example,
    if a standard cell is instatntiated and needs x, y, or z dimensional
    arguments, the arguments will be the number of pixels and the
    physical value will be the argument mutliplied by the pixel scalar.
    """
    def set_scale_parameters(self, px, layer):
        self.px_     = px
        self.layer_  = layer
        print(f"px set to: {px} mm/px\nlayer set to: {layer} mm/layer", )

    """
    This sets the render resoultion when exported to openSCAD.
    """
    def set_render_resolution(self, res):
        self.res_ = res
        print(f"Rendering fragment number set to: {res}")

    """
    This sets the scale used in the lef/def files for 1 pixel. For example,
    if 1 pixel is equivalent to 0.5 units in the lef/def file then this value
    should be set to 0.5.
    """
    def set_def_scale(self, def_scale):
        self.def_scale_ = def_scale
        print(f".def unit scale set to: {def_scale}")


    """
    This sets the pixel pitch of the PNR flow as determined by the platform.
    """
    def set_pitch(self, pitch):
        self.pitch_ = pitch
        print(f"The platform pitch is {pitch} pixels.")

    """
    This sets the phyical location that the bottom routing layer is placed.
    """
    def set_bottom_layer(self, bottom_layer) :
        self.bottom_layer_ = bottom_layer * self.layer_
        print(f"The bottom layer is set to: {bottom_layer} of {int(self.z_bdim_/self.layer_)} layers")

    """
    This sets the multiple of layers per via.
    """
    def set_layers_per_via(self, lpv) :
        self.lpv_ = lpv
        print(f"The number of layer per via is set to: {lpv} layers/via")

    """
    This sets the dimensions of the bulk chip.
    """
    def set_bulk_dimensions(self, x_bdim, y_bdim, z_bdim) :
        self.x_bdim_ = x_bdim * self.px_
        self.y_bdim_ = y_bdim * self.px_
        self.z_bdim_ = z_bdim * self.layer_
        print(f"Bulk dimensions are:\n\tx: {x_bdim} px\n\ty: {y_bdim} px\n\tz: {z_bdim}  layers")

    """
    This sets the dimensions of the chip.
    """
    def set_chip_dimensions(self, x_cdim, y_cdim) :
        self.x_cdim_ = x_cdim
        self.y_cdim_ = y_cdim
        self.cleft = (x_cdim[0]+1) * self.def_scale_
        self.cright = (x_cdim[1]-1) * self.def_scale_
        self.cbottom = (y_cdim[0]+1) * self.def_scale_
        self.ctop = (y_cdim[1]-1) * self.def_scale_

        print(f"The lower and upper bounds of the chip are:\n\tx: [{x_cdim[0]} {x_cdim[1]}] px\n\ty: [{y_cdim[0]} {y_cdim[1]}] px")

    """
    This initializes the tensor of the design space.
    """
    def design_space_init(self, xspace: int, yspace: int, num_layers: int) :
        ys =  int(yspace/self.pitch_)+1
        xs = int(xspace/self.pitch_)+1
        self.design_space_       = np.zeros((num_layers, ys, xs), dtype=np.bool_)
        self.design_space_nets_  = np.empty((num_layers, ys, xs), dtype=object)

    def scale_value(self, x):
        return self.px_*x/self.def_scale_

    def scale_point(self, point):
        return map(self.scale_value,point)

    def scale_dimension(self, dimm):
        x, y, z = dimm
        x = self.px_*x
        y = self.px_*y
        z = z*self.layer_
        return (x,y,z)

    def layer_number(self, layer):
        i = 0
        for l in self.db.getTech().getLayers():
            if layer.getConstName() == l.getConstName():
                return i
            if l.getType() == "ROUTING":
                i += 1
        raise ValueError()

    def layer_height(self, layer):
        return self.layer_number(layer)*self.lpv_*self.layer_+self.bottom_layer_

    def net_dimm(self, net):
        route_params  = self.get_route_params()
        return route_params.get(net.getName(), [14, 14, 10])

    def set_dimm_file(self, dimm_file):
        self.dimm_file = dimm_file

    def get_route_params(self):
        if self.route_params == None:
            if self.dimm_file == None or self.dimm_file.strip()=='':
                self.route_params = dict()
            else:
                from csv import reader
                with open(self.dimm_file) as f:
                    params = list(reader(f))
                self.route_params = {param[0]:list(map(int, param[1:4])) for param in params if len(param) == 4}
        return self.route_params

class place:
    """
    This class takes a .def file with place information and can get the 2D components
    found in the file as well as the placement location and transform that information
    to openSCAD with the corresponding 3D components.
    """
    def __init__(self, db, params):
        self.params = params
        self.db = db
        self.mapOrient = {"R180": "S",
                          "R0": "N",
                          "MY": "FN",
                          "MX": "FS"}
    def get_components(self):
        block = self.db.getChip().getBlock()
        # TODO abstract dimension calculations
        def_scale_ = self.params.def_scale_
        bottom_layer_ = self.params.bottom_layer_
        layer_ = self.params.layer_
        for i in block.getInsts():
            name = i.getName()
            orient = self.mapOrient[i.getOrient()]
            macro = i.getMaster().getName()
            x, y = i.getLocation()
            xd = x/def_scale_
            yd = y/def_scale_
            zd = bottom_layer_/layer_
            try:
                yield scad_std_cell.__dict__[macro](xd, yd, zd, orient)
            except KeyError:
                # Attempt P-Cell parsing
                # Macro name might be BaseName_Param1_Param2...
                # e.g. p_serpentine_1_180_30_8 -> p_serpentine_1(..., 180, 30, 8)
                found = False
                # Sort bases by length desc to match longest prefix (avoid matching p_serpentine when p_serpentine_1 exists)
                candidates = sorted([k for k in scad_std_cell.__dict__ if not k.startswith('__')], key=len, reverse=True)
                for base in candidates:
                    if macro.startswith(base) and len(macro) > len(base) and macro[len(base)] == '_':
                         suffix = macro[len(base)+1:]
                         try:
                             params = [float(p) if '.' in p else int(p) for p in suffix.split('_')]
                             print(f"DEBUG: Resolved P-Cell {macro} -> {base} with params {params}")
                             yield scad_std_cell.__dict__[base](xd, yd, zd, orient, *params)
                             found = True
                             break
                         except ValueError:
                             continue # Not purely numeric params, maybe not match
                if not found:
                     print(f"Error: Macro {macro} not found in SCAD library.")
                     raise

    def place_components(self):
        components_placed = list(self.get_components())

        if len(components_placed) > 0:
            return reduce(operator.add, components_placed)
        else:
            return scad_std_cell.empty_obj('NO COMPONENTS')

class route:
    """
    This class takes a .def file with routing information and creates a SCAD model of the routing channels.
    """
    def __init__(self, db, params) :
        self.db = db
        self.params = params

    def wire_iter(self, wire):
        dec = odb.dbWireDecoder()
        dec.begin(wire)
        opcode = dec.next()
        while opcode != odb.dbWireDecoder.END_DECODE:
            layer = dec.getLayer()
            if opcode == odb.dbWireDecoder.BTERM:
                term = dec.getBTerm()
                yield (opcode, layer, (term,))
            elif opcode == odb.dbWireDecoder.ITERM:
                term = dec.getITerm()
                yield (opcode, layer, (term,))
            elif opcode == odb.dbWireDecoder.JUNCTION:
                wire_type = dec.getWireType()
                jid = dec.getJunctionId()
                jval = dec.getJunctionValue()
                yield (opcode, layer, (wire_type, jid, jval))
            elif opcode == odb.dbWireDecoder.PATH or opcode == odb.dbWireDecoder.VWIRE or opcode == odb.dbWireDecoder.SHORT:
                wire_type = dec.getWireType()
                yield (opcode, layer, (wire_type,))
            elif opcode == odb.dbWireDecoder.POINT or opcode == odb.dbWireDecoder.POINT_EXT:
                point = dec.getPoint()
                prop = dec.getProperty()
                yield (opcode, layer, (point, prop))
            elif opcode == odb.dbWireDecoder.RECT:
                rect = dec.getRect()
                yield (opcode, layer, (rect,))
            elif opcode == odb.dbWireDecoder.RULE:
                rule = dec.getRule()
                yield (opcode, layer, (rule,))
            elif opcode == odb.dbWireDecoder.TECH_VIA:
                via = dec.getTechVia()
                yield (opcode, layer, (via,))
            elif opcode == odb.dbWireDecoder.VIA:
                via = dec.getVia()
                yield (opcode, layer, (via,))
            else:
                raise ValueError()
            opcode = dec.next()

    def segment_iter(self, wire):
        last = None
        for (opcode, layer, vals) in self.wire_iter(wire):
            if opcode == odb.dbWireDecoder.PATH or opcode == odb.dbWireDecoder.VWIRE or opcode == odb.dbWireDecoder.SHORT:
                last = None
            elif opcode == odb.dbWireDecoder.POINT or opcode == odb.dbWireDecoder.POINT_EXT:
                (point, prop) = vals
                if len(point) == 2:
                    # No extension — use raw DEF coordinates so routes
                    # align exactly with via endpoints.
                    point = (point[0], point[1], 0)
                if last is not None:
                    yield (layer, last, point)
                last = point
            elif opcode == odb.dbWireDecoder.TECH_VIA:
                (via,) = vals
                if last is not None:
                    yield (layer, last, via)
                last = via
            elif opcode == odb.dbWireDecoder.VIA:
                (via,) = vals
                if last is not None:
                    yield (layer, last, via)
                last = via
            else:
                raise NotImplementedError()

    def generate_dimm(self, wchan, xychan, hchan):
        return [
            [
                [0, 0],
                [-wchan/2, wchan/2],
                [0, hchan]
            ],
            [
                [-wchan/2, wchan/2],
                [0, 0],
                [0, hchan]
            ],
            [
                [-xychan/2, xychan/2],
                [-xychan/2, xychan/2],
                [0, 0]
            ]
        ]

    def add_channel(self, layer, net, start, end):
        dimm = self.generate_dimm(*self.params.scale_dimension(self.params.net_dimm(net)))
        ax, ay, _ = self.params.scale_point(start)
        if type(end) == odb.dbTechVia or type(end) == odb.dbVia:
            height = self.params.layer_height(end.getBottomLayer())
            via_height = self.params.layer_height(end.getTopLayer())
            p0 = [ax, ay, height]
            p1 = [ax, ay, via_height]
            connect_matrix = [["z", p1, 2]]
        else:
            height = self.params.layer_height(layer)
            bx, by, _ = self.params.scale_point(end)
            if ax == bx:
                p0 = [ax, ay, height]
                p1 = [bx, by, height]
                connect_matrix = [["y", p1, 1]]
            else:
                p0 = [ax, ay, height]
                p1 = [bx, by, height]
                connect_matrix = [["x", p1, 0]]
        return scad_routing.routing(p0, connect_matrix, dimm)

    def segment_length(self, layer, net, start, end):
        ax, ay, aext = self.params.scale_point(start)
        if type(end) == odb.dbTechVia or type(end) == odb.dbVia:
            height = self.params.layer_height(end.getBottomLayer())
            via_height = self.params.layer_height(end.getTopLayer())
            return via_height - height
        else:
            bx, by, bext = self.params.scale_point(end)
            return math.sqrt((by-ay)**2 + (bx-ax)**2)

    def report_route_lengths(self, output_dir, design):
        lengths = dict()
        for net in self.db.getChip().getBlock().getNets():
            total = 0
            wire = net.getWire()
            if wire is None:
                continue
            for layer, start, end in self.segment_iter(wire):
                total += self.segment_length(layer, net, start, end)
            lengths[net.getName()] = total

        df = pd.DataFrame(lengths, index=['length (mm)'])
        df.to_csv(os.path.join(output_dir, design + "_lengths.csv"))

    def generate_channels(self):
        block = self.db.getChip().getBlock()
        nets = block.getNets()
        for net in nets:
            wire = net.getWire()
            if wire is None:
                continue
            for (layer, start, end) in self.segment_iter(wire):
                yield self.add_channel(layer, net, start, end)

    def perform_routing(self):
        routing = list(self.generate_channels())
        if routing:
            return reduce(operator.add, routing)
        else:
            return scad_std_cell.empty_obj('NO ROUTING')

class pin_place:
    """
    This class takes a .def file with pin information and places pins or pinholes accordingly.
    """
    def __init__(self, db, params) :
        self.db = db
        self.params = params

    def place_pinholes(self):
        # TODO abstract dimension calculations
        cy = self.params.y_bdim_/self.params.px_
        cx = self.params.x_bdim_/self.params.px_

        pinholes_placed = []
        for term in self.db.getChip().getBlock().getBTerms():
            for pin in term.getBPins():
                for box in pin.getBoxes():
                    layer = box.getTechLayer()
                    ax, ay = box.xMin(), box.yMin()
                    bx, by = box.xMax(), box.yMax()
                    ax, ay = self.params.scale_point((ax, ay))
                    bx, by = self.params.scale_point((bx, by))
                    x = (ax + bx)/2
                    y = (ay + by)/2
                    z = self.params.layer_height(layer)
                    if ax <= self.params.cleft:
                        x,y,z,ori = (0, y, z, 'left')
                    elif bx >= self.params.cright:
                        x,y,z,ori = (cb, y, z, 'right')
                    elif ay <= self.params.cbottom:
                        x,y,z,ori = (x, 0, z, 'bottom')
                    elif by >= self.params.ctop:
                        x,y,z,ori = (x, cy, z, 'top')
                    else:
                        continue
                    pinholes_placed.append(scad_std_cell.pinhole_325px_0(x, y, z, ori))
        if pinholes_placed:
            return reduce(operator.add, pinholes_placed)
        else:
            return scad_std_cell.empty_obj('NO PINHOLES')

    def generate_dimm(self, xychan, ychan, zchan):
        px_ = self.params.px_
        return [[[-xychan*px_/2, xychan*px_/2], [-xychan*px_/2, xychan*px_/2], [0, 0]]]

    def place_interconnect(self):
        # TODO abstract dimension calculations
        layer_ = self.params.layer_
        x_bdim_ = self.params.x_bdim_
        y_bdim_ = self.params.y_bdim_
        z_bdim_ = self.params.z_bdim_
        px_ = self.params.px_
        inter_x = solid.utils.floor(x_bdim_/px_/2)
        inter_y = solid.utils.floor(y_bdim_/px_/2)
        inter_z = z_bdim_/layer_
        pins_placed = []

        for term in self.db.getChip().getBlock().getBTerms():
            net = term.getNet()
            dimm = self.generate_dimm(*self.params.net_dimm(net))
            dimm_x, dimm_y, dimm_z = self.params.scale_point(self.params.net_dimm(net))
            for pin in term.getBPins():

                for box in pin.getBoxes():
                    layer = box.getTechLayer()
                    ax, ay = box.xMin(), box.yMin()
                    bx, by = box.xMax(), box.yMax()
                    contain_x_left    = ax >= self.params.cleft
                    contain_x_right   = bx <= self.params.cright
                    contain_y_bottom  = ay >= self.params.cbottom
                    contain_y_top     = by <= self.params.ctop
                    ax, ay = self.params.scale_point((ax, ay))
                    bx, by = self.params.scale_point((bx, by))
                    z_bot = self.params.layer_height(layer)
                    x = (ax + bx)/2
                    y = (ay + by)/2
                    z_top = z_bdim_
                    if contain_x_left and contain_x_right and contain_y_bottom and contain_y_top:
                        # slight overlap for z (10% of layer height)
                        p0 = [x, y, z_bot - (self.params.layer_ * 0.1)]
                        p1 = [x, y, z_top]
                        connect_matrix = [["z", p1, 0]]
                        pins_placed.append(scad_routing.routing(p0, connect_matrix, dimm))
        if pins_placed:
            print(f"Pin '{term.getName()}' is located inside of the chip boundary.")
            print("Using interconnect module - ensure pins are alligned correctly in io_constraints.tcl.")
            return scad_std_cell.interconnect_32channel(inter_x, inter_y, inter_z), reduce(operator.add, pins_placed)
        else:
            return scad_std_cell.empty_obj('NO INTERCONNECT'), scad_std_cell.empty_obj('NO PINS')

class add_bulk:
    """
    This class creates the bulk chip.
    """
    def __init__(self,params) :
        self.x_dim = params.x_bdim_
        self.y_dim = params.y_bdim_
        self.z_dim = params.z_bdim_

    def bulk(self):
        bulk_chip = solid.cube([self.x_dim, self.y_dim, self.z_dim])
        return(bulk_chip)

class add_marker:
    """
    This class creates a marker on the chip for orientation.
    """
    def __init__(self, params):
        self.params = params

    def marker(self):
        xpos = self.params.x_bdim_-200*self.params.px_
        ypos = self.params.y_bdim_-200*self.params.px_
        zpos = self.params.z_bdim_-200*self.params.px_
        return scad_std_cell.marker(xpos, ypos, zpos)

class scad_generation:
    """
    This class generates the dependent scad files for the design.
    """
    def __init__(self) :
        pass

    def generate_routing_scad(self, design, routing_file, output_dir):
        """Generates the routing scad and writes to the results directory."""
        os.makedirs(output_dir, exist_ok=True)
        out_file = os.path.join(output_dir, design + "_routing.scad")
        with open(routing_file) as f:
            with open(out_file, "w") as f1:
                for line in f:
                    f1.write(line)
        return out_file

    def generate_std_cell_scad(self, px, layer, lpv, design, component_file, output_dir, scad_include_files=None):

        """Generates the standard cell scad with the pixel and layers defined."""
        os.makedirs(output_dir, exist_ok=True)
        out_file = os.path.join(output_dir, design + "_components.scad")

        # Copy dependencies referenced in component_file
        comp_dir = os.path.dirname(component_file)
        with open(component_file) as f:
            content = f.read()
        
        # Check if px, layer, lpv are already defined in the component file
        # to avoid duplicate variable definitions
        has_px = any(line.strip().startswith('px =') or line.strip().startswith('px=') for line in content.splitlines())
        has_layer = any(line.strip().startswith('layer =') or line.strip().startswith('layer=') for line in content.splitlines())
        has_lpv = any(line.strip().startswith('lpv =') or line.strip().startswith('lpv=') for line in content.splitlines())
        
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('use <') and line.endswith('>'):
                # Extract filename: use <filename.scad>
                ref_file = line[5:-1]
                # Check if it exists in component directory
                src_path = os.path.join(comp_dir, ref_file)
                if os.path.exists(src_path):
                    dst_path = os.path.join(output_dir, os.path.basename(ref_file))
                    if not os.path.exists(dst_path):
                        try:
                            shutil.copy2(src_path, dst_path)
                            print(f"DEBUG: Copied dependency {ref_file} to results.")
                        except Exception as e:
                            print(f"Warning: Failed to copy dependency {ref_file}: {e}")

        # Copy scad_include files to output directory
        if scad_include_files:
            for include_file in scad_include_files:
                if os.path.exists(include_file):
                    dst_path = os.path.join(output_dir, os.path.basename(include_file))
                    if not os.path.exists(dst_path):
                        try:
                            shutil.copy2(include_file, dst_path)
                            print(f"DEBUG: Copied include file {os.path.basename(include_file)} to results.")
                        except Exception as e:
                            print(f"Warning: Failed to copy include file {include_file}: {e}")

        with open(out_file, "w") as f1:
            f1.write(f"use <{design}_routing.scad>\n")
            # Only write px/layer/lpv if not already defined in content
            if not has_px:
                f1.write(f"px = {px};\n")
            if not has_layer:
                f1.write(f"layer = {layer};\n")
            if not has_lpv:
                f1.write(f"lpv = {lpv};\n")
            f1.write("\n")
            f1.write(content)
        return out_file

def scad_pnr(db, component_file, routing_file, platform, design, def_file, results_dir, px, layer, bottom_layer, lpv, xbulk, ybulk, zbulk, xchip, ychip, pitch, res, dimm_file = None, scad_include_files = None):
    """This function generates the entire SCAD flow by calling the classes above in their intended order."""

    print("------------------------------")
    print("SCAD Place and Route begin")
    print("------------------------------\n")

    print("Generating standard cell and routing SCAD...")
    scad_routing_file = scad_generation().generate_routing_scad(design, routing_file, results_dir)
    scad_std_file = scad_generation().generate_std_cell_scad(px, layer, lpv, design, component_file, results_dir, scad_include_files)
    print("SCAD generation complete\n")

    print(f"Importing generated SCAD for design '{design}'")
    cwd = os.getcwd()
    try:
        # Switch to results dir to force relative path imports in generated logic
        os.chdir(results_dir)
        global scad_routing, scad_std_cell
        scad_std_cell   = solid.import_scad(os.path.basename(scad_std_file))
        scad_routing    = solid.import_scad(os.path.basename(scad_routing_file))
    finally:
        os.chdir(cwd)
    print(f"SCAD import for '{design}' complete\n")

    print(f"The design parameters for '{design}' are:")
    params = Params(db)
    params.set_def_scale(db.getTech().getDbUnitsPerMicron())
    params.set_pitch(pitch)
    params.set_scale_parameters(px, layer)
    params.set_bulk_dimensions(xbulk, ybulk, zbulk)
    params.set_chip_dimensions(xchip, ychip)
    params.set_bottom_layer(bottom_layer)
    params.set_dimm_file(dimm_file)
    params.set_layers_per_via(lpv)

    print("\nInitializing design space")
    params.design_space_init(xbulk, ybulk, 10)
    params.set_render_resolution(res)
    print("Initialization complete.")

    print(f"\nBuilding the design model for '{design}' from:\n'{def_file}'")
    bulk = add_bulk(params).bulk()
    routing = route(db, params).perform_routing()
    components =  place(db, params).place_components()
    pinholes = pin_place(db, params).place_pinholes()
    interconnect, pins = pin_place(db, params).place_interconnect()
    marker = add_marker(params).marker()
    negative = components + pinholes + pins + marker + solid.color("orange")(routing)
    model = bulk - negative  + solid.color("blue", alpha=0.1)(interconnect)
    #model = negative
    print("Build complete\n")

    route(db, params).report_route_lengths(results_dir, design)

    print(f"Rendering build for '{design}'")
    solid.scad_render_to_file(model,
                              f"{results_dir}/{design}.scad",
                              file_header=f"$fn = {params.res_};",
                              include_orig_code=False)
    print(f"Rendering complete\n")

    # Post-process the generated SCAD file to ensure relative paths
    out_scad_path = f"{results_dir}/{design}.scad"
    if os.path.exists(out_scad_path):
        print(f"DEBUG: Post-processing {out_scad_path} for relative paths...")
        with open(out_scad_path, 'r') as f:
            content = f.read()
        
        # Replace absolute paths with basenames for portability
        # Look for "use </absolute/path/to/file.scad>" -> "use <file.scad>"
        lines = content.splitlines()
        new_lines = []
        modified_count = 0
        for line in lines:
            if line.strip().startswith('use <') and '/' in line:
                # Extract path
                start = line.find('<') + 1
                end = line.find('>')
                if start > 0 and end > start:
                    full_path = line[start:end]
                    basename = os.path.basename(full_path)
                    print(f"DEBUG: Replacing '{full_path}' with '{basename}'")
                    line = f"use <{basename}>"
                    modified_count += 1
            new_lines.append(line)
        
        if modified_count > 0:
            with open(out_scad_path, 'w') as f:
                f.write('\n'.join(new_lines))
            print(f"Enforced relative paths in SCAD output ({modified_count} lines updated).")
        else:
            print("No absolute paths found to replace.")

    print("------------------------------")
    print("SCAD Place and Route complete")
    print("------------------------------\n")

    print(f"Place and Route results are found in '{results_dir}'")

    if args.stl:
        scad_file = f"{args.results_dir}/{args.design}.scad"
        stl_file = f"{args.results_dir}/{args.design}.stl"
        print(f"Generating STL for '{args.design}'...")
        
        if args.profile:
            profile_path = os.path.join(os.path.dirname(__file__), "..", "slicer", "profiles", f"{args.profile}.json")
            if os.path.exists(profile_path):
                print(f"Using Printer Profile: {args.profile}")
                with open(profile_path, 'r') as f:
                    print(f.read())
            else:
                print(f"Warning: Profile {args.profile} not found at {profile_path}")

        # Ensure openscad is in path
        if shutil.which("openscad"):
            try:
                subprocess.run(["openscad", "-o", stl_file, scad_file], check=True)
                print(f"STL generated: {stl_file}")
            except subprocess.CalledProcessError as e:
                print(f"Error generating STL: {e}")
        else:
            print("Warning: OpenSCAD not found in path. Skipping STL generation.")

if __name__ == "__main__":
    import argparse

    import subprocess

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--stl', action='store_true', help="Generate STL output from SCAD.")
    ap.add_argument('--profile', metavar='<profile>', dest='profile', type=str,
                    help="Printer profile name.")
    ap.add_argument('--platform', metavar='<platform>', dest='platform', type=str,
                    help="Design platform.")
    ap.add_argument('--design', metavar='<design_name>', dest='design', type=str,
                    help="The design name.")
    ap.add_argument('--def_file', metavar='<path>', dest='def_file', type=str,
                    help="Path to the .def file from OpenROAD flow.")
    ap.add_argument('--lef_file', metavar='<path>', dest='lef_file', type=str, action='append',
                    help="Path to the .lef file from OpenROAD flow.")
    ap.add_argument('--routing_file', metavar='<path>', dest='routing_file', type=str,
                    help="Path to the scad routing definitions.")
    ap.add_argument('--component_file', metavar='<path>', dest='component_file', type=str,
                    help="Path to the scad component definitions.")
    ap.add_argument('--tlef_file', metavar='<path>', dest='tlef_file', type=str,
                    help="Path to the .tlef file from OpenROAD flow.")
    ap.add_argument('--results_dir', metavar='<path>', dest='results_dir', type=str,
                    help="Path where the results are generated.")
    ap.add_argument('--px', metavar='<value>', dest='px', type=float,
                    help="Metric pixel size.")
    ap.add_argument('--layer', metavar='<value>', dest='layer', type=float,
                    help="Metric layer size.")
    ap.add_argument('--bottom_layer', metavar='<value>', dest='bottom_layer', type=int,
                    help="Value of bottom layer (routing).")
    ap.add_argument('--lpv', metavar='<value>', dest='lpv', type=int,
                    help="Multiples of layers per via.")
    ap.add_argument('--xbulk', metavar='<value>', dest='xbulk', type=int,
                    help="Horizontal length of the bulk in pixels.")
    ap.add_argument('--ybulk', metavar='<value>', dest='ybulk', type=int,
                    help="Vertical length of the bulk in pixels.")
    ap.add_argument('--zbulk', metavar='<value>', dest='zbulk', type=int,
                    help="Height of the bulk in layers.")
    ap.add_argument('--xchip', metavar='<values>', dest='xchip', nargs = '+', type=int,
                    help="Left and right endpoints of chip in multiples of pixels.")
    ap.add_argument('--ychip', metavar='<values>', dest='ychip', nargs = '+', type=int,
                    help="Bottom and top endpoints of chip in multiples of pixels.")
    ap.add_argument('--pitch', metavar='<value>', dest='pitch', type=int,
                    help="PNR pitch for the platform.")
    ap.add_argument('--res', metavar='<value>', dest='res', type=int,
                    help="Resolution of the scad rendering.")
    ap.add_argument('--dimm_file', metavar='<path>', dest='dimm_file', type=str,
                    help="Optional .csv file with routing dimensions.", default = None)
    ap.add_argument('--pcell_file', metavar='<path>', dest='pcell_file', type=str,
                    help="Optional .csv file with pcell parameters.", default = None)
    ap.add_argument('--scad_include', metavar='<path>', dest='scad_include', type=str, nargs='*',
                    help="Optional SCAD files to include (e.g., lef_scad_config.scad).", default = None)
    args = ap.parse_args()

    db = odb.dbDatabase.create()
    print(f"DEBUG: Reading TLEF: {args.tlef_file}")
    try:
        odb.read_lef(db, args.tlef_file)
    except Exception as e:
        print(f"Error reading TLEF {args.tlef_file}: {e}")
        # TLEF is critical usually, but let's see.

    if isinstance(args.lef_file, str):
        print(f"DEBUG: Reading LEF (str): {args.lef_file}")
        try:
            odb.read_lef(db, args.lef_file)
        except Exception as e:
            print(f"Error reading LEF {args.lef_file}: {e}")

    if isinstance(args.lef_file, list):
        for lef in args.lef_file:
            print(f"DEBUG: Reading LEF (list item): {lef}")
            try:
                odb.read_lef(db, lef)
            except Exception as e:
                print(f"Error reading LEF {lef}: {e}")
    if not args.def_file:
        print("Error: No DEF file provided. Ensure the pnr flow completed successfully first.")
        sys.exit(1)
    if not os.path.exists(args.def_file):
        print(f"Error: DEF file {args.def_file} does not exist.")
        sys.exit(1)
    # Patch for ODB API which expects tech, not db
    tech = db.getTech()
    odb.read_def(tech, args.def_file)
    scad_pnr(db,
             args.component_file,
             args.routing_file,
             args.platform,
             args.design,
             args.def_file,
             args.results_dir,
             args.px,
             args.layer,
             args.bottom_layer,
             args.lpv,
             args.xbulk,
             args.ybulk,
             args.zbulk,
             args.xchip,
             args.ychip,
             args.pitch,
             args.res,
             args.dimm_file,
             args.scad_include)
