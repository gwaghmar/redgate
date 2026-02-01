import json
import os
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "comparison_cache.json"
        self.metadata_file = self.cache_dir / "metadata.json"
    
    def save_comparison_data(self, data):
        """Save comparison results to cache"""
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, default=str)
            logger.info(f"Comparison data saved to cache: {self.cache_file}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}", exc_info=True)
            raise
        
        # Save metadata separately for quick access
        metadata = {
            'last_updated': cache_data['timestamp'],
            'databases': list(data.get('databases', {}).keys()) if isinstance(data.get('databases'), dict) else []
        }
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def load_comparison_data(self):
        """Load cached comparison data"""
        if not self.cache_file.exists():
            logger.debug("Cache file does not exist")
            return None
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            logger.info(f"Comparison data loaded from cache: {self.cache_file}")
            return cache_data
        except Exception as e:
            logger.error(f"Error loading cache: {e}", exc_info=True)
            return None
    
    def get_cache_metadata(self):
        """Get cache metadata without loading full data"""
        if not self.metadata_file.exists():
            return None
        
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return None
    
    def cache_exists(self):
        """Check if cache exists"""
        return self.cache_file.exists()
    
    def clear_cache(self):
        """Clear all cached data"""
        if self.cache_file.exists():
            os.remove(self.cache_file)
        if self.metadata_file.exists():
            os.remove(self.metadata_file)
