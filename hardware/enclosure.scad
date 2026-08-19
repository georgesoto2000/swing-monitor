// Swing Monitor - shaft-mount enclosure
// Parametric OpenSCAD model driven by hardware/encloser.md
//
// Design (see chat / README for full rationale):
//  - Two-piece shell: "base" (5 closed sides, open top) + flat "lid"
//    that snaps into the open top via a thin flexible lip with a
//    perimeter bead, which pops into a matching groove in the cavity
//    wall - same thin-wall-interference idea as the shaft clip below,
//    just applied as a rectangular loop instead of a circular one.
//  - A pry notch is cut into one end of the base's rim so there's
//    somewhere to get a fingernail/thin tool under the lid to release
//    the bead and lift it off (it clicks shut positively, so a flush
//    friction-only seam would be very hard to open).
//  - A C-section clip is fused to the underside of the base and snaps
//    over the shaft (gap faces down/out; mouth is narrower than the
//    shaft so the arms flex open on insertion, then spring back).
//  - Case Y axis runs parallel to the shaft (per encloser.md: "Y axis
//    of the PCB should point up the shaft").
//
// Assumptions made beyond encloser.md (flagged in chat - revisit after
// a test fit):
//  - encloser.md's PCB+battery box (45 x 70 x 30) is treated as the
//    required INTERNAL cavity, not an outer envelope.
//  - 2mm shell walls, 1.6mm clip walls, 1.2mm lid-lip walls (thin
//    enough to flex for PLA snap-fits).
//  - No standoffs/screw bosses - real PCB mounting hole positions
//    aren't specified yet, so the cavity is left empty and the board
//    is expected to be held with foam tape until that's nailed down.
//  - Bead/groove sizes are a first-pass guess at PLA's flex - print
//    and test; loosen (reduce bead_h) if it's too tight to open,
//    tighten if it doesn't hold.

$fn = 64;

// ---- tunable parameters ----
shaft_d      = 13;    // shaft diameter at the mount point (mm)
box_x        = 45;    // internal cavity width  (X)
box_y        = 70;    // internal cavity length (Y) - parallel to shaft
box_z        = 30;    // internal cavity height (Z)
wall         = 2;     // shell wall thickness (mm)
clip_wall    = 1.6;   // shaft clip wall thickness (mm)
clip_gap_deg = 70;    // arc left open at the clip mouth (deg)
lip_h        = 5;     // lid lip depth (mm)
lip_wall     = 1.2;   // lid lip wall thickness (thin, so it can flex)
lid_clear    = 0.2;   // nominal lid-to-cavity fit clearance per side (mm)
bead_h       = 0.4;   // snap-bead radial projection beyond the lip (mm)
bead_band    = 1.6;   // height of the bead / matching groove band (mm)
groove_clear = 0.15;  // extra clearance in the groove vs the bead (mm)
notch_w      = 10;    // pry-notch width, cut into the rim at y=0 (mm)
notch_d      = 5;     // pry-notch depth, down from the rim (mm)

// ---- derived ----
out_x      = box_x + 2*wall;
out_y      = box_y + 2*wall;
clip_r_in  = shaft_d/2;
clip_r_out = clip_r_in + clip_wall;
lip_ox     = box_x - 2*lid_clear;               // lip outer footprint
lip_oy     = box_y - 2*lid_clear;
lip_ix     = lip_ox - 2*lip_wall;                // lip inner (hollow) footprint
lip_iy     = lip_oy - 2*lip_wall;
groove_x   = lip_ox + 2*bead_h + 2*groove_clear; // groove cut footprint
groove_y   = lip_oy + 2*bead_h + 2*groove_clear;

function arc_pts(r, a0, a1, n=32) =
    [ for (i = [0:n]) let(a = a0 + (a1-a0)*i/n) [r*cos(a), r*sin(a)] ];

module pie(r, a0, a1) {
    polygon(concat([[0, 0]], arc_pts(r, a0, a1)));
}

module clip_2d() {
    difference() {
        difference() {
            circle(r = clip_r_out);
            circle(r = clip_r_in);
        }
        // gap centered straight down (-Z once oriented) for shaft insertion
        pie(clip_r_out * 1.5, -90 - clip_gap_deg/2, -90 + clip_gap_deg/2);
    }
}

module shaft_clip() {
    // sink the tube up into the base far enough that a real slice of
    // it (not just its topmost edge) sits inside the base's bottom
    // slab, so the union is a true volumetric weld, not a knife-edge
    // touch (which CGAL/slicers can treat as two separate solids)
    embed = clip_wall;
    translate([0, 0, -(clip_r_out - wall + embed)])
        translate([0, out_y, 0])
            rotate([90, 0, 0])
                linear_extrude(height = out_y)
                    clip_2d();
}

module groove_2d() {
    difference() {
        square([groove_x, groove_y], center = true);
        square([box_x, box_y], center = true);
    }
}

module pry_notch() {
    // through the y=0 end wall, from the rim down by notch_d
    translate([-notch_w/2, -1, box_z + wall - notch_d])
        cube([notch_w, wall + 2, notch_d + 1]);
}

module base_shell() {
    difference() {
        translate([-out_x/2, 0, 0])
            cube([out_x, out_y, box_z + wall]);
        translate([-box_x/2, wall, wall])
            cube([box_x, box_y, box_z + 1]); // open top
        // groove that the lid's snap-bead pops into once fully seated
        translate([0, wall + box_y/2, wall + box_z - lip_h])
            linear_extrude(height = bead_band)
                groove_2d();
        pry_notch();
    }
}

module base() {
    union() {
        base_shell();
        shaft_clip();
    }
}

module lip_ring(ox, oy, ix, iy, h) {
    linear_extrude(height = h)
        difference() {
            square([ox, oy], center = true);
            square([ix, iy], center = true);
        }
}

module lid() {
    union() {
        // flat cap - matches the base's outer footprint, rests on the rim
        translate([-out_x/2, 0, 0])
            cube([out_x, out_y, wall]);
        // thin flexible lip - centered on the cavity, drops down into it
        translate([0, wall + box_y/2, -lip_h])
            lip_ring(lip_ox, lip_oy, lip_ix, lip_iy, lip_h);
        // snap bead at the tip (leading edge on insertion) - pops into
        // the base's groove once the lid is fully seated
        translate([0, wall + box_y/2, -lip_h])
            lip_ring(lip_ox + 2*bead_h, lip_oy + 2*bead_h, lip_ix, lip_iy, bead_band);
    }
}

// lid re-oriented flat-side-down for support-free printing
// (its "assembled" pose above has the lip hanging below the cap)
module lid_print_ready() {
    translate([0, 0, wall])
        mirror([0, 0, 1])
            lid();
}

module assembled_preview() {
    color("SteelBlue") base();
    translate([0, 0, box_z + wall])
        color("Orange", 0.9) lid();
}

// ---- render selection ----
// part = "assembled" | "base" | "lid"
part = "assembled";

if (part == "assembled") assembled_preview();
else if (part == "base") base();
else if (part == "lid") lid_print_ready();
