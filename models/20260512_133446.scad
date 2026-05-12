difference() {
  cylinder(h=15, r1=2, r2=0);
  translate([-8, -8, -2])
  rotate([90, 0, 0])
  difference() {
    cylinder(h=3, r1=2, r2=0);
    translate([-4, -4, -1])
    rotate([90, 0, 0])
    difference() {
      cylinder(h=1, r1=1.5, r2=0);
      translate([-2, -2, -0.5])
      rotate([90, 0, 0])
    }
  }
}

// Rocket tail
translate([0, 0, -3])
cylinder(h=4, r1=5, r2=0);

// Propellant tanks
translate([0, 0, 0])
difference() {
  cylinder(h=10, r1=1.5, r2=0);
  translate([-5, -5, -1])
  rotate([90, 0, 0])
  difference() {
    cylinder(h=3, r1=1.5, r2=0);
    translate([-4, -4, -0.5])
    rotate([90, 0, 0])
  }
}

// Rocket fins
translate([0, 0, -10])
rotate([90, 0, 0])
difference() {
  cylinder(h=2, r1=0.5, r2=0);
  translate([-3, -3, -0.25])
  rotate([90, 0, 0])
}