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
def download_mall_dataset(target_dir):
    """
    Downloads the Mall dataset if not already present.
    Falls back to manual instructions if automatic download fails.
    """
    import urllib.request
    import zipfile

    frames_dir = os.path.join(target_dir, "frames")
    gt_file    = os.path.join(target_dir, "mall_gt.mat")

    if os.path.exists(frames_dir) and os.path.exists(gt_file):
        print("✅ Mall dataset already present — skipping download")
        return

    os.makedirs(target_dir, exist_ok=True)

    # Primary mirror (Kaggle-hosted ZIP)
    url = "https://personal.ie.cuhk.edu.hk/~ccloy/files/datasets/mall_dataset.zip"
    zip_path = os.path.join(target_dir, "mall_dataset.zip")

    print(f"📥 Downloading Mall dataset from {url} ...")
    try:
        urllib.request.urlretrieve(url, zip_path)
        print("✅ Download complete — extracting...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(target_dir)
        os.remove(zip_path)
        print(f"✅ Mall dataset extracted to {target_dir}")
    except Exception as e:
        print(f"⚠️  Automatic download failed: {e}")
        print("    Please download the Mall dataset manually from:")
        print("    https://personal.ie.cuhk.edu.hk/~ccloy/downloads_mall_dataset.html")
        print(f"    and extract it to: {target_dir}")
        print("    Expected layout:")
        print(f"      {target_dir}/frames/seq_000001.jpg ... seq_002000.jpg")
        print(f"      {target_dir}/mall_gt.mat")
        raise


class MallDataset(Dataset):
    """
    PyTorch Dataset for the Mall Crowd Counting dataset.

    2000 surveillance frames from a shopping mall lobby.
    Crowd counts range from 13 to 53 people per frame.

    Ground truth: mall_gt.mat
      frame[0, i]['loc'][0, 0]   → (N, 2) array of (x, y) head positions
      frame[0, i]['count'][0, 0] → scalar count (redundant; we derive from loc)
    Images: frames/seq_XXXXXX.jpg  (1-indexed, zero-padded to 6 digits)
    """

    def __init__(self, data_path, split="train", image_size=(512, 512),
                 train_ratio=0.8):
        self.image_size = image_size
        self.samples    = []

        gt_path = os.path.join(data_path, "mall_gt.mat")
        if not os.path.exists(gt_path):
            raise FileNotFoundError(
                f"Mall GT not found at {gt_path}. "
                "Run download_mall_dataset() first."
            )

        gt_data = sio.loadmat(gt_path)
        frames_cell = gt_data["frame"]          # shape (1, 2000)
        n_total     = frames_cell.shape[1]

        split_idx = int(n_total * train_ratio)
        indices   = range(0, split_idx) if split == "train" else range(split_idx, n_total)

        for i in indices:
            img_path = os.path.join(data_path, "frames", f"seq_{i+1:06d}.jpg")
            if not os.path.exists(img_path):
                continue
            # Extract (N, 2) head-location array for this frame
            loc = frames_cell[0, i][0, 0][0]   # 'loc' is first structured field
            self.samples.append((img_path, loc))

        print(f"✅ MallDataset [{split}]: {len(self.samples)} frames loaded")

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
        img_path, loc = self.samples[idx]

        image          = Image.open(img_path).convert("RGB")
        orig_w, orig_h = image.size

        # loc may be (N, 2) or (2,) for single-person frames
        points = np.array(loc, dtype=np.float32)
        if points.ndim == 1:
            points = points.reshape(1, -1)

        density_map = generate_density_map((orig_h, orig_w), points, sigma=8)

        target_h = self.image_size[0] // 8
        target_w = self.image_size[1] // 8
        density_map_resized = scipy.ndimage.zoom(
            density_map,
            (target_h / orig_h, target_w / orig_w),
            order=1
        )

        if density_map_resized.sum() > 0 and len(points) > 0:
            density_map_resized = density_map_resized * (
                len(points) / density_map_resized.sum()
            )

        image_tensor   = self.transform(image)
        density_tensor = torch.tensor(
            density_map_resized, dtype=torch.float32
        ).unsqueeze(0)

        return image_tensor, density_tensor, len(points)


def get_finetune_dataloaders(mall_path, batch_size=4, image_size=(512, 512)):
    """
    Returns train and val DataLoaders for Mall fine-tuning.
    80 % of the 2000 frames for training, 20 % for validation.
    """
    train_ds = MallDataset(mall_path, split="train", image_size=image_size)
    val_ds   = MallDataset(mall_path, split="val",   image_size=image_size)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=1,          shuffle=False, num_workers=0)

    print(f"📂 Mall fine-tune — train: {len(train_ds)}, val: {len(val_ds)}")
    return train_loader, val_loader


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