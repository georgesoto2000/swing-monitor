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
//  - A solid rectangular ring is fused to the underside of the base,
//    bored through with a circular hole for the shaft plus a straight
//    capture slot connecting the bore to the outside (gap facing
//    down). It's installed by clipping it sideways onto the shaft at
//    a point where the shaft is already narrower than the slot (no
//    flexing needed to get it on), then sliding it up the taper until
//    the bore wedges tight at the 13mm mounting point. Because the
//    slot width sits between "narrow enough to clip on" and "too
//    narrow to slip back off at 13mm", it self-retains without ever
//    needing to flex - so the ring can be fully rigid.
//    (v1 used a thin C-clip that snapped on radially by flexing open
//    over the full 13mm - it cracked in testing: PLA has very low
//    elongation at break, and the clip also put a sharp stress-riser
//    right at the weakest print-adhesion seam. v2 tried a fully closed
//    sliding sleeve, but that can't get past a fixed/epoxied clubhead.
//    This version avoids both problems - no flex, and installs without
//    removing the head.)
//  - slot_w = 10.5mm: measured shaft diameter at the clip-on point is
//    ~9mm, so this gives ~1.5mm clearance to clip on without force
//    (also covers FDM holes typically printing a touch undersized),
//    while staying 2.5mm under shaft_d (13mm) so the ring can't slip
//    sideways back off once slid up to the mount point. If the fit
//    feels wrong either way after printing, it's a one-line tweak.
//  - Case Y axis runs parallel to the shaft (per encloser.md: "Y axis
//    of the PCB should point up the shaft").
//
// Assumptions made beyond encloser.md (flagged in chat - revisit after
// a test fit):
//  - encloser.md's PCB+battery box (45 x 70 x 30) is treated as the
//    required INTERNAL cavity, not an outer envelope.
//  - 2mm shell walls, 1.2mm lid-lip walls (thin enough to flex for a
//    PLA snap-fit - the lid still relies on flexing, unlike the sleeve).
//  - Sleeve bore is sized shaft_d + slide_clearance for an easy slide
//    fit; nothing here guarantees it stops/grips exactly at the 13mm
//    point without knowing the real taper profile, so plan on a wrap
//    of grip tape over the sleeve's top edge (traps it from sliding
//    further up) and/or a dab of glue for final retention.
//  - PCB (veroboard, screwed through a flange) sits on two 5mm-tall
//    bosses with blind M2.5 self-tap pilot holes rather than one
//    continuous ledge - same holding strength for a 2-point mount,
//    less material/print time. boss_pos below is a PLACEHOLDER
//    (centered in X, guessed spacing in Y) - it has not been checked
//    against your actual flange hole positions, update it to match
//    before printing for real.
//  - Bead/groove sizes on the lid are a first-pass guess at PLA's
//    flex - print and test; loosen (reduce bead_h) if it's too tight
//    to open, tighten if it doesn't hold.

$fn = 64;

// ---- tunable parameters ----
shaft_d      = 13;    // shaft diameter at the mount point (mm)
box_x        = 45;    // internal cavity width  (X)
box_y        = 70;    // internal cavity length (Y) - parallel to shaft
box_z        = 30;    // internal cavity height (Z)
wall         = 2;     // shell wall thickness (mm)
slide_clear  = 0.4;   // sleeve bore clearance over shaft_d, for sliding on (mm)
sleeve_wall  = 4;     // sleeve wall thickness - rigid, no flex needed (mm)
sleeve_chamfer = 1.2; // lead-in chamfer at the sleeve's ends (mm)
sleeve_overlap = 1.5; // how far the sleeve's top face sits inside the
                       // base's bottom slab (0..wall), for a solid weld
slot_w       = 10.5;  // capture-slot width (mm) - see note above:
                       // shaft-diameter-at-clip-on-point < slot_w < shaft_d
lip_h        = 5;     // lid lip depth (mm)
lip_wall     = 1.2;   // lid lip wall thickness (thin, so it can flex)
lid_clear    = 0.2;   // nominal lid-to-cavity fit clearance per side (mm)
bead_h       = 0.4;   // snap-bead radial projection beyond the lip (mm)
bead_band    = 1.6;   // height of the bead / matching groove band (mm)
groove_clear = 0.15;  // extra clearance in the groove vs the bead (mm)
notch_w      = 10;    // pry-notch width, cut into the rim at y=0 (mm)
notch_d      = 5;     // pry-notch depth, down from the rim (mm)
boss_h       = 5;     // PCB standoff boss height, off the cavity floor (mm)
boss_od      = 6;     // boss outer diameter (mm)
pilot_d      = 2.0;   // pilot hole diameter for a self-tapping M2.5 (mm)
pilot_depth  = 4.5;   // blind pilot hole depth from the boss top (mm)
// PLACEHOLDER positions (x, y) in cavity-local coords: x=0 is the
// cavity centreline, y=0..box_y runs the cavity's length - MUST be
// updated to match your veroboard flange's real hole spacing
boss_pos     = [[0, 15], [0, 55]];

// on/off switch hole - straight through-hole in the +X long wall,
// for a panel-mount toggle/rocker switch (6mm is a common bushing
// size for these - check it matches whatever switch you buy, and
// that its bushing is rated for a ~2mm panel, i.e. the wall thickness)
hole_d       = 6;     // hole diameter (mm)
hole_below_lip = 5;   // "5mm lower than the ledge for the lid" - measured
                       // from the BOTTOM of the lid's lip (z = box_z+wall-lip_h),
                       // not the rim itself, since the rim sits right in the
                       // snap-groove band and a hole there would weaken it

// ---- derived ----
out_x      = box_x + 2*wall;
out_y      = box_y + 2*wall;
sleeve_id  = shaft_d + slide_clear;
sleeve_od  = sleeve_id + 2*sleeve_wall;
lip_ox     = box_x - 2*lid_clear;               // lip outer footprint
lip_oy     = box_y - 2*lid_clear;
lip_ix     = lip_ox - 2*lip_wall;                // lip inner (hollow) footprint
lip_iy     = lip_oy - 2*lip_wall;
groove_x   = lip_ox + 2*bead_h + 2*groove_clear; // groove cut footprint
groove_y   = lip_oy + 2*bead_h + 2*groove_clear;

module shaft_sleeve() {
    // rigid block: circular bore for the shaft, plus a straight
    // capture slot (constant width slot_w) connecting the bore to the
    // outside at the bottom, so the shaft clips in sideways rather
    // than needing to be threaded through an end
    z_center = sleeve_overlap - sleeve_od/2;
    translate([0, 0, z_center]) {
        difference() {
            translate([-sleeve_od/2, 0, -sleeve_od/2])
                cube([sleeve_od, out_y, sleeve_od]);
            rotate([-90, 0, 0])
                cylinder(d = sleeve_id, h = out_y + 2, center = false);
            // lead-in chamfers at both ends so it doesn't catch/scrape
            // as it's slid up the shaft's taper, either way round
            rotate([-90, 0, 0])
                cylinder(d1 = sleeve_id + 2*sleeve_chamfer, d2 = sleeve_id,
                         h = sleeve_chamfer);
            translate([0, out_y - sleeve_chamfer, 0])
                rotate([-90, 0, 0])
                    cylinder(d1 = sleeve_id, d2 = sleeve_id + 2*sleeve_chamfer,
                             h = sleeve_chamfer);
            // capture slot - straight channel from the bore's centre
            // (local z=0) down through the block's bottom face
            translate([-slot_w/2, -1, -sleeve_od/2 - 1])
                cube([slot_w, out_y + 2, sleeve_od/2 + 1]);
        }
    }
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

module side_hole() {
    // on/off switch, panel-mounted through the +X long wall, centered
    // along the case length
    hole_z = (box_z + wall - lip_h) - hole_below_lip;
    translate([out_x/2 - wall - 2, wall + box_y/2, hole_z])
        rotate([0, 90, 0])
            cylinder(d = hole_d, h = wall + 4);
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
        side_hole();
    }
}

module pcb_boss(pos) {
    // solid pillar off the cavity floor with a blind pilot hole from
    // the top - screw drives down through the veroboard flange into it
    translate([pos[0], wall + pos[1], wall])
        difference() {
            cylinder(d = boss_od, h = boss_h);
            translate([0, 0, boss_h - pilot_depth])
                cylinder(d = pilot_d, h = pilot_depth + 1);
        }
}

module pcb_bosses() {
    for (p = boss_pos) pcb_boss(p);
}

module base() {
    union() {
        base_shell();
        shaft_sleeve();
        pcb_bosses();
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
