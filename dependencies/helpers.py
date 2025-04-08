import math
def distributeObjects(objects, aspect_ratio):
    num_objects = len(objects);
    height = int(math.sqrt(num_objects / aspect_ratio));
    width = int(aspect_ratio * height);

    while width * height < num_objects:
        if width <= height * aspect_ratio:
            width += 1;
        else:
            height += 1;

    matrix = [];
    obj_iter = iter(objects)
    for _ in range(height):
        row = [];
        for _ in range(width):
            try:
                row.append(next(obj_iter));
            except StopIteration:
                break;
        if row: 
            matrix.append(row);

    return matrix;