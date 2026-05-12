cylinder(h=20, r1=10, r2=5);

// Create the nose
translate([-5, 4, 30])
    cylinder(h=10, r=1);

// Create the eyes
translate([-5, -5, 27])
    sphere(r=2);
translate([5, -5, 27])
    sphere(r=2);