from skyforge.vision import train_forest
from skyforge.scene import ROOT
print(train_forest(ROOT/"data/synthetic",ROOT/"models"))
