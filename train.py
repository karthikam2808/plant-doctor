import os
import torch
import timm
import json
from tqdm import tqdm
from torch import nn, optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from sklearn.model_selection import train_test_split

# --- Parameters ---
data_dir = "dataset"
model_name = "tf_efficientnetv2_b3"
batch_size = 16
epochs = 5
lr = 0.001
model_save_path = "model/model.pth"
index_json_path = "model/class_indices.json"

# --- Transforms ---
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

# --- Dataset ---
print("📂 Loading dataset...")
full_dataset = datasets.ImageFolder(root=data_dir, transform=transform)
class_to_idx = full_dataset.class_to_idx
idx_to_class = {v: k for k, v in class_to_idx.items()}

# Save class_indices.json
os.makedirs("model", exist_ok=True)
with open(index_json_path, "w") as f:
    json.dump(idx_to_class, f, indent=4)

# --- Split dataset ---
train_idx, val_idx = train_test_split(list(range(len(full_dataset))), test_size=0.2, stratify=full_dataset.targets)
train_subset = torch.utils.data.Subset(full_dataset, train_idx)
val_subset = torch.utils.data.Subset(full_dataset, val_idx)

train_loader = DataLoader(train_subset, batch_size=batch_size, shuffle=True)
val_loader = DataLoader(val_subset, batch_size=batch_size)

# --- Load EfficientNetV2 ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = timm.create_model(model_name, pretrained=True, num_classes=len(class_to_idx))
model.to(device)

# --- Loss & Optimizer ---
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=lr)

# --- Training loop ---
print(f"\n🚀 Starting training with {model_name} for {epochs} epochs on {len(class_to_idx)} classes...")

for epoch in range(epochs):
    model.train()
    total_loss, correct = 0, 0
    print(f"\n🔁 Epoch {epoch+1}/{epochs}")

    for batch_idx, (inputs, labels) in enumerate(tqdm(train_loader, desc="🧪 Training", unit="batch")):
        inputs, labels = inputs.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        _, preds = torch.max(outputs, 1)
        correct += torch.sum(preds == labels).item()

# Optional: Show per-batch info
tqdm.write(f"   🔹 Batch {batch_idx+1} | Loss: {loss.item():.4f} | Accuracy so far: {100 * correct / ((batch_idx+1) * batch_size):.2f}%")
epoch_acc = 100 * correct / len(train_subset)
print(f"✅ Epoch {epoch+1} completed | Avg Loss: {total_loss:.4f} | Accuracy: {epoch_acc:.2f}%")

# --- Save model ---
torch.save(model.state_dict(), model_save_path)
print(f"\n✅ Model saved to {model_save_path}")
print(f"✅ Class index mapping saved to {index_json_path}")
