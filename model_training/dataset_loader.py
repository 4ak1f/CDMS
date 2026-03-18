import os
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import scipy.io as sio
import scipy.ndimage
import torchvision.transforms as transforms


def generate_density_map(image_shape, points, sigma=15):
    """
    Converts point annotations (dot per person) into a smooth density map.
    Each person's dot becomes a Gaussian blob.
    Sum of density map = total number of people.
    
    Args:
        image_shape: (height, width) of the image
        points: array of (x, y) coordinates, one per person
        sigma: size of Gaussian blur (larger = smoother map)
    """
    density_map = np.zeros(image_shape, dtype=np.float32)

    if len(points) == 0:
        return density_map

    for point in points:
        x, y = int(min(point[0], image_shape[1] - 1)), int(min(point[1], image_shape[0] - 1))
        if x >= 0 and y >= 0:
            density_map[y, x] = 1.0

    # Apply Gaussian blur to spread each dot into a density region
    density_map = scipy.ndimage.gaussian_filter(density_map, sigma=sigma)

    # Normalize so sum equals actual person count
    if density_map.sum() > 0:
        density_map = density_map * (len(points) / density_map.sum())

    return density_map


class ShanghaiTechDataset(Dataset):
    """
    PyTorch Dataset for ShanghaiTech crowd counting.
    Loads images and their corresponding ground truth density maps.
    """

    def __init__(self, data_path, part="A", split="train", image_size=(512, 512)):
        self.image_size = image_size
        self.samples = []

        # Build path to images and ground truth
        split_folder = "train_data" if split == "train" else "test_data"
        img_dir = os.path.join(data_path, f"part_{part}", split_folder, "images")
        gt_dir = os.path.join(data_path, f"part_{part}", split_folder, "ground-truth")

        if not os.path.exists(img_dir):
            raise FileNotFoundError(f"Dataset not found at {img_dir}")

        # Match each image with its ground truth file
        for img_file in sorted(os.listdir(img_dir)):
            if not img_file.endswith(".jpg"):
                continue
            img_id = os.path.splitext(img_file)[0]  # e.g. IMG_1
            gt_file = f"GT_{img_id}.mat"
            gt_path = os.path.join(gt_dir, gt_file)
            img_path = os.path.join(img_dir, img_file)

            if os.path.exists(gt_path):
                self.samples.append((img_path, gt_path))

        print(f"Loaded {len(self.samples)} samples from Part {part} {split} set")

        # Image preprocessing
        self.transform = transforms.Compose([
            transforms.Resize(image_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],  # ImageNet mean
                std=[0.229, 0.224, 0.225]    # ImageNet std
            )
        ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, gt_path = self.samples[idx]

        # Load image
        image = Image.open(img_path).convert("RGB")
        orig_w, orig_h = image.size

        # Load ground truth points from .mat file
        gt_data = sio.loadmat(gt_path)
        points = gt_data["image_info"][0][0][0][0][0]  # (N, 2) array of x,y coords

        # Generate density map at original size then resize
        density_map = generate_density_map((orig_h, orig_w), points)

        # Resize density map to match model output size (image_size / 8 due to pooling)
        target_h = self.image_size[0] // 8
        target_w = self.image_size[1] // 8
        density_map_resized = scipy.ndimage.zoom(
            density_map,
            (target_h / orig_h, target_w / orig_w),
            order=1
        )

        # Scale so sum still equals person count
        if density_map_resized.sum() > 0:
            density_map_resized = density_map_resized * (points.shape[0] / density_map_resized.sum())

        image_tensor = self.transform(image)
        density_tensor = torch.tensor(density_map_resized, dtype=torch.float32).unsqueeze(0)

        return image_tensor, density_tensor, points.shape[0]  # image, density map, true count


def get_dataloaders(data_path, part="A", batch_size=4, image_size=(512, 512)):
    """Creates train and test dataloaders."""
    train_dataset = ShanghaiTechDataset(data_path, part=part, split="train", image_size=image_size)
    test_dataset = ShanghaiTechDataset(data_path, part=part, split="test", image_size=image_size)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False, num_workers=0)

    return train_loader, test_loader
def get_combined_dataloaders(data_path, batch_size=4, image_size=(512, 512)):
    """
    Combines ShanghaiTech Part A and Part B for training.
    Part A = ultra dense crowds
    Part B = moderate crowds
    Together = much better generalisation
    """
    from torch.utils.data import ConcatDataset

    # Load both parts
    train_a = ShanghaiTechDataset(data_path, part="A", split="train", image_size=image_size)
    train_b = ShanghaiTechDataset(data_path, part="B", split="train", image_size=image_size)

    # Combine training sets
    combined_train = ConcatDataset([train_a, train_b])

    # Keep test sets separate for proper evaluation
    test_a = ShanghaiTechDataset(data_path, part="A", split="test", image_size=image_size)
    test_b = ShanghaiTechDataset(data_path, part="B", split="test", image_size=image_size)
    combined_test = ConcatDataset([test_a, test_b])

    train_loader = DataLoader(combined_train, batch_size=batch_size, shuffle=True, num_workers=0)
    test_loader  = DataLoader(combined_test,  batch_size=1,          shuffle=False, num_workers=0)

    print(f"Combined training set: {len(combined_train)} images")
    print(f"Combined test set:     {len(combined_test)} images")

    return train_loader, test_loader
class JHUCrowdDataset(Dataset):
    """
    PyTorch Dataset for JHU-Crowd++ crowd counting.
    Ground truth format: x y width height class occlusion
    One person per line in .txt files.
    """

    def __init__(self, data_path, split="train", image_size=(512, 512)):
        self.image_size = image_size
        self.samples = []

        img_dir = os.path.join(data_path, split, "images")
        gt_dir  = os.path.join(data_path, split, "gt")

        if not os.path.exists(img_dir):
            raise FileNotFoundError(f"JHU dataset not found at {img_dir}")

        for img_file in sorted(os.listdir(img_dir)):
            if not img_file.endswith(".jpg"):
                continue
            img_id   = os.path.splitext(img_file)[0]
            gt_path  = os.path.join(gt_dir,  f"{img_id}.txt")
            img_path = os.path.join(img_dir, img_file)

            if os.path.exists(gt_path):
                self.samples.append((img_path, gt_path))

        print(f"Loaded {len(self.samples)} samples from JHU-Crowd++ {split} set")

        self.transform = transforms.Compose([
            transforms.Resize(image_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, gt_path = self.samples[idx]

        # Load image
        image    = Image.open(img_path).convert("RGB")
        orig_w, orig_h = image.size

        # Load ground truth points from txt file
        points = []
        with open(gt_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    x, y = float(parts[0]), float(parts[1])
                    points.append([x, y])

        points = np.array(points) if points else np.zeros((0, 2))

        # Generate density map
        density_map = generate_density_map((orig_h, orig_w), points)

        # Resize density map
        target_h = self.image_size[0] // 8
        target_w = self.image_size[1] // 8
        density_map_resized = scipy.ndimage.zoom(
            density_map,
            (target_h / orig_h, target_w / orig_w),
            order=1
        )

        # Scale so sum equals person count
        if density_map_resized.sum() > 0 and len(points) > 0:
            density_map_resized = density_map_resized * (len(points) / density_map_resized.sum())

        image_tensor   = self.transform(image)
        density_tensor = torch.tensor(density_map_resized, dtype=torch.float32).unsqueeze(0)

        return image_tensor, density_tensor, len(points)
def get_all_dataloaders(shanghai_path, jhu_path, batch_size=4, image_size=(512, 512)):
    """
    Combines ALL datasets:
    - ShanghaiTech Part A (ultra dense)
    - ShanghaiTech Part B (moderate)
    - JHU-Crowd++ (diverse real world)
    Total: ~2000+ training images
    """
    from torch.utils.data import ConcatDataset

    print("Loading all datasets...")

    # ShanghaiTech
    train_a = ShanghaiTechDataset(shanghai_path, part="A", split="train", image_size=image_size)
    train_b = ShanghaiTechDataset(shanghai_path, part="B", split="train", image_size=image_size)

    # JHU-Crowd++
    train_jhu = JHUCrowdDataset(jhu_path, split="train", image_size=image_size)
    val_jhu   = JHUCrowdDataset(jhu_path, split="val",   image_size=image_size)

    # Combine everything
    combined_train = ConcatDataset([train_a, train_b, train_jhu, val_jhu])

    # Test sets
    test_a   = ShanghaiTechDataset(shanghai_path, part="A", split="test", image_size=image_size)
    test_b   = ShanghaiTechDataset(shanghai_path, part="B", split="test", image_size=image_size)
    test_jhu = JHUCrowdDataset(jhu_path, split="test", image_size=image_size)
    combined_test = ConcatDataset([test_a, test_b, test_jhu])

    train_loader = DataLoader(combined_train, batch_size=batch_size, shuffle=True,  num_workers=0)
    test_loader  = DataLoader(combined_test,  batch_size=1,          shuffle=False, num_workers=0)

    print(f"✅ Total training images: {len(combined_train)}")
    print(f"✅ Total test images:     {len(combined_test)}")

    return train_loader, test_loader