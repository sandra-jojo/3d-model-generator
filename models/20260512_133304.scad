union() function. Here's an example:


// Head shape
head = cylinder(h=18, r=4, center=true);

// Body shape
body = translate([0,0,4]) cube([26,35,7], center=true);

// Tail shape
tail = translate([0,-2,4]) cylinder(h=20, r=10, center=true);

// Cat shape
cat_shape = union() {
  head;
  body;
  tail;
};

rotate_x(90) rotate_y(-90) cat_shape;