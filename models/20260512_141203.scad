union() {
    translate([0, 10, -5])
        cube([5, 2, 15], center=true);

    translate([-4, 8, -7])
        sphere(1, center=true, $fn=20);

    translate([3, 8, -7])
        cylinder(h=6, r=0.75, center=true);
}