sphere(r=20);

    // Legs
    for (i=[0:3]) {
        translate(legs[i]) sphere(r=10);
    }
};

// Print the chair to the console
print(chair);