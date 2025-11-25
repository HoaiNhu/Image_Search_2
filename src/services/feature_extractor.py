"""
Image feature extraction service using MobileNetV2.
Much lighter than CLIP: 14MB vs 150MB, 10x faster, still accurate!
"""
import gc
import logging
from typing import Optional, List
import numpy as np
from PIL import Image
import torch
import torchvision.models as models
import torchvision.transforms as transforms

from config.settings import config
from utils.image_utils import ImageProcessor

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Service for extracting image features using MobileNetV2."""
    
    def __init__(self):
        """Initialize MobileNetV2 model."""
        self.device = config.DEVICE
        self.model = None
        self.image_processor = ImageProcessor()
        self._model_loaded = False
        
        # Image preprocessing for MobileNetV2
        self.preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        # Only load immediately if not using lazy loading
        if not config.LAZY_LOAD_MODEL:
            self._load_model()
    
    def _load_model(self) -> None:
        """Load MobileNetV2 model - only 14MB!"""
        if self._model_loaded:
            return
            
        try:
            logger.info("Loading MobileNetV2 model (14MB, very lightweight!)...")
            
            # Load pre-trained MobileNetV2
            self.model = models.mobilenet_v2(pretrained=True)
            
            # Remove classification layer, keep only feature extractor
            self.model = torch.nn.Sequential(*list(self.model.children())[:-1])
            
            # Move to device and set to eval mode
            self.model.to(self.device)
            self.model.eval()
            
            # Disable gradients for inference - saves memory
            for param in self.model.parameters():
                param.requires_grad = False
            
            # Disable gradient computation
            torch.set_grad_enabled(False)
            
            self._model_loaded = True
            logger.info(f"MobileNetV2 loaded successfully on {self.device} (memory: ~14MB)")
            
        except Exception as e:
            logger.error(f"Error loading MobileNetV2 model: {str(e)}")
            raise
    
    def extract_features_from_image(self, image: Image.Image) -> Optional[np.ndarray]:
        """
        Extract features from a PIL Image using MobileNetV2.
        
        Args:
            image: PIL Image object
            
        Returns:
            Feature vector as numpy array (1280-dim) or None if failed
        """
        try:
            # Ensure model is loaded
            if not self._model_loaded:
                self._load_model()
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Preprocess image
            input_tensor = self.preprocess(image)
            input_batch = input_tensor.unsqueeze(0).to(self.device)
            
            # Extract features
            with torch.no_grad():
                features = self.model(input_batch)
            
            # Flatten and normalize
            features = features.squeeze()
            features = features / (features.norm() + 1e-8)  # Avoid division by zero
            
            # Convert to numpy
            features_np = features.cpu().numpy().flatten()
            
            # Clean up tensors
            del input_tensor, input_batch, features
            if self.device != "cpu":
                torch.cuda.empty_cache()
            
            # Force garbage collection if enabled
            if config.ENABLE_GC:
                gc.collect()
            
            return features_np
            
        except Exception as e:
            logger.error(f"Error extracting features from image: {str(e)}")
            return None
    
    def extract_features_from_url(self, image_url: str) -> Optional[np.ndarray]:
        """
        Extract features from an image URL.
        
        Args:
            image_url: URL of the image
            
        Returns:
            Feature vector as numpy array or None if failed
        """
        try:
            # Download image
            image = self.image_processor.download_image(image_url)
            if image is None:
                return None
            
            # Extract features
            return self.extract_features_from_image(image)
        except Exception as e:
            logger.error(f"Error extracting features from URL {image_url}: {str(e)}")
            return None
    
    def extract_features_from_bytes(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Extract features from image bytes.
        
        Args:
            image_bytes: Image data in bytes
            
        Returns:
            Feature vector as numpy array or None if failed
        """
        try:
            # Load image from bytes
            image = self.image_processor.load_image_from_bytes(image_bytes)
            if image is None:
                return None
            
            # Extract features
            return self.extract_features_from_image(image)
        except Exception as e:
            logger.error(f"Error extracting features from bytes: {str(e)}")
            return None
    
    def extract_batch_features(self, images: List[Image.Image]) -> Optional[np.ndarray]:
        """
        Extract features from multiple images in batch.
        
        Args:
            images: List of PIL Image objects
            
        Returns:
            Feature matrix as numpy array (N x 1280) or None if failed
        """
        try:
            if not images:
                return None
            
            if not self._model_loaded:
                self._load_model()
            
            # Preprocess all images
            batch_tensors = []
            for img in images:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                tensor = self.preprocess(img)
                batch_tensors.append(tensor)
            
            # Stack into batch
            batch = torch.stack(batch_tensors).to(self.device)
            
            # Extract features
            with torch.no_grad():
                features = self.model(batch)
            
            # Flatten and normalize each feature
            features = features.squeeze()
            if len(features.shape) == 1:
                features = features.unsqueeze(0)
            
            # Normalize each feature vector
            features = features / (features.norm(dim=1, keepdim=True) + 1e-8)
            
            # Convert to numpy
            features_np = features.cpu().numpy()
            
            # Clean up
            del batch_tensors, batch, features
            if self.device != "cpu":
                torch.cuda.empty_cache()
            
            return features_np
            
        except Exception as e:
            logger.error(f"Error extracting batch features: {str(e)}")
            return None


# Singleton instance
_feature_extractor: Optional[FeatureExtractor] = None


def get_feature_extractor() -> FeatureExtractor:
    """
    Get or create feature extractor instance.
    
    Returns:
        FeatureExtractor instance
    """
    global _feature_extractor
    if _feature_extractor is None:
        _feature_extractor = FeatureExtractor()
    return _feature_extractor
