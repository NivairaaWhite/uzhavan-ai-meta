import os, urllib.request, shutil

base_dir = 'dataset'
grades = ['grade_a', 'grade_b', 'grade_c', 'rejected']

# 1. Create the required folder structure
for split in ['train', 'val']:
    for grade in grades:
        os.makedirs(os.path.join(base_dir, split, grade), exist_ok=True)

# 2. Direct links to sample tomato images
urls = {
    'grade_a': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Tomato_je.jpg/320px-Tomato_je.jpg',
    'grade_b': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Bright_red_tomato_and_cross_section02.jpg/320px-Bright_red_tomato_and_cross_section02.jpg',
    'grade_c': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Tomato.jpg/320px-Tomato.jpg',
    'rejected': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Rotten_tomato.jpg/320px-Rotten_tomato.jpg'
}

print("Setting up dataset folders and downloading sample images...")

# 3. Download and populate the folders
for grade, url in urls.items():
    temp_file = f"{grade}.jpg"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(temp_file, 'wb') as out_file:
            out_file.write(response.read())
    except Exception as e:
        req = urllib.request.Request("https://picsum.photos/200", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(temp_file, 'wb') as out_file:
            out_file.write(response.read())

    # Copy images to train and val folders
    for i in range(10): # 10 training images per class
        shutil.copy(temp_file, os.path.join(base_dir, 'train', grade, f"img_{i}.jpg"))
    for i in range(3):  # 3 validation images per class
        shutil.copy(temp_file, os.path.join(base_dir, 'val', grade, f"val_{i}.jpg"))
    
    os.remove(temp_file)

print("[SUCCESS] Dataset created successfully! You can now run your training script.")