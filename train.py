import argparse
import copy
import os
from pathlib import Path
from collections import Counter

import torch
import torch.nn as nn
from efficientnet_pytorch import EfficientNet
from PIL import Image
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, random_split, WeightedRandomSampler
from torchvision import datasets, transforms

os.environ.setdefault("TORCH_HOME", os.path.join(os.getcwd(), ".torch"))

MODEL_NAME = "efficientnet-b0"
IMAGE_SIZE = 224
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def rgb_loader(path):
    with Image.open(path) as image:
        return image.convert("RGB")


class DeepfakeDetector(nn.Module):
    def __init__(self, use_pretrained=True):
        super().__init__()
        if use_pretrained:
            try:
                self.model = EfficientNet.from_pretrained(MODEL_NAME)
                print("Loaded pretrained EfficientNet-B0 backbone.")
            except Exception as error:
                print(f"Could not load pretrained backbone: {error}")
                print("Falling back to randomly initialized EfficientNet-B0.")
                self.model = EfficientNet.from_name(MODEL_NAME)
        else:
            self.model = EfficientNet.from_name(MODEL_NAME)

        self.model._fc = nn.Linear(self.model._fc.in_features, 2)

    def forward(self, x):
        return self.model(x)


def build_checkpoint(model, classes, args, best_val_accuracy):
    return {
        "state_dict": model.state_dict(),
        "class_names": classes,
        "image_size": IMAGE_SIZE,
        "mean": MEAN,
        "std": STD,
        "best_val_accuracy": best_val_accuracy,
        "model_name": MODEL_NAME,
        "args": vars(args),
    }


def build_transforms():
    train_transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1, hue=0.02),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])

    eval_transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])

    return train_transform, eval_transform


def load_datasets(data_dir, val_dir=None, val_split=0.2, seed=42):
    train_transform, eval_transform = build_transforms()

    if val_dir:
        train_dataset = datasets.ImageFolder(data_dir, transform=train_transform, loader=rgb_loader)
        val_dataset = datasets.ImageFolder(val_dir, transform=eval_transform, loader=rgb_loader)
        return train_dataset, val_dataset, train_dataset.classes

    full_dataset = datasets.ImageFolder(data_dir, transform=train_transform, loader=rgb_loader)
    classes = full_dataset.classes

    val_size = max(1, int(len(full_dataset) * val_split))
    train_size = len(full_dataset) - val_size
    if train_size <= 0:
        raise ValueError("Dataset is too small. Add more images or reduce --val-split.")

    generator = torch.Generator().manual_seed(seed)
    train_subset, val_subset = random_split(full_dataset, [train_size, val_size], generator=generator)

    train_dataset = copy.deepcopy(full_dataset)
    val_dataset = copy.deepcopy(full_dataset)
    train_dataset.transform = train_transform
    val_dataset.transform = eval_transform
    train_dataset.samples = [full_dataset.samples[index] for index in train_subset.indices]
    train_dataset.targets = [full_dataset.targets[index] for index in train_subset.indices]
    val_dataset.samples = [full_dataset.samples[index] for index in val_subset.indices]
    val_dataset.targets = [full_dataset.targets[index] for index in val_subset.indices]

    return train_dataset, val_dataset, classes


def run_epoch(model, loader, criterion, optimizer, device, training):
    if training:
        model.train()
    else:
        model.eval()

    total_loss = 0.0
    total_correct = 0
    total_examples = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        if training:
            optimizer.zero_grad()

        with torch.set_grad_enabled(training):
            outputs = model(images)
            loss = criterion(outputs, labels)
            if training:
                loss.backward()
                optimizer.step()

        total_loss += loss.item() * images.size(0)
        predictions = outputs.argmax(dim=1)
        total_correct += (predictions == labels).sum().item()
        total_examples += images.size(0)

    average_loss = total_loss / max(1, total_examples)
    accuracy = total_correct / max(1, total_examples)
    return average_loss, accuracy


def build_balanced_sampler(dataset):
    target_counts = Counter(dataset.targets)
    class_weights = {
        class_index: len(dataset.targets) / (len(target_counts) * count)
        for class_index, count in target_counts.items()
    }
    sample_weights = [class_weights[target] for target in dataset.targets]
    sampler = WeightedRandomSampler(
        weights=torch.DoubleTensor(sample_weights),
        num_samples=len(sample_weights),
        replacement=True,
    )
    return sampler, target_counts, class_weights


def main():
    parser = argparse.ArgumentParser(description="Train DeepShield on a real/fake image dataset.")
    parser.add_argument("--data-dir", required=True, help="Path to dataset root or train directory.")
    parser.add_argument("--val-dir", help="Optional validation dataset directory.")
    parser.add_argument("--output", default="efficientnet_b0_deepfake.pth", help="Output model weights path.")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs.")
    parser.add_argument("--batch-size", type=int, default=8, help="Training batch size.")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate.")
    parser.add_argument("--val-split", type=float, default=0.2, help="Validation split if --val-dir is not provided.")
    parser.add_argument("--workers", type=int, default=0, help="DataLoader worker count.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--no-pretrained", action="store_true", help="Disable pretrained EfficientNet weights.")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    train_dataset, val_dataset, classes = load_datasets(
        data_dir=args.data_dir,
        val_dir=args.val_dir,
        val_split=args.val_split,
        seed=args.seed,
    )

    if sorted(classes) != ["fake", "real"]:
        print(f"Detected classes: {classes}")
        print("Expected class folders named 'fake' and 'real'. Training will continue with detected ordering.")

    train_sampler, train_counts, class_weights = build_balanced_sampler(train_dataset)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, sampler=train_sampler, num_workers=args.workers)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)

    model = DeepfakeDetector(use_pretrained=not args.no_pretrained).to(device)
    class_weight_tensor = torch.tensor(
        [class_weights[class_index] for class_index in range(len(classes))],
        dtype=torch.float32,
        device=device,
    )
    criterion = nn.CrossEntropyLoss(weight=class_weight_tensor)
    optimizer = Adam(model.parameters(), lr=args.lr)
    scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=1)

    best_state = copy.deepcopy(model.state_dict())
    best_val_accuracy = 0.0

    print(f"Training samples: {len(train_dataset)}")
    print(f"Validation samples: {len(val_dataset)}")
    print(f"Class order: {classes}")
    print(f"Training class counts: {dict(train_counts)}")
    print(f"Loss class weights: {class_weight_tensor.detach().cpu().tolist()}")

    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc = run_epoch(model, train_loader, criterion, optimizer, device, training=True)
        val_loss, val_acc = run_epoch(model, val_loader, criterion, optimizer, device, training=False)
        scheduler.step(val_loss)

        print(
            f"Epoch {epoch}/{args.epochs} | "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} | "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )

        if val_acc >= best_val_accuracy:
            best_val_accuracy = val_acc
            best_state = copy.deepcopy(model.state_dict())

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.load_state_dict(best_state)
    checkpoint = build_checkpoint(model, classes, args, best_val_accuracy)
    torch.save(checkpoint, output_path)
    print(f"Saved best model weights to: {output_path}")
    print(f"Best validation accuracy: {best_val_accuracy:.4f}")


if __name__ == "__main__":
    main()
