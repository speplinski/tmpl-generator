from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from tmpl_generator.configs.mask_config import MaskConfig
from .image_processor import ImageProcessor
from .system_monitor import SystemMonitor

class MaskManager:
    """
    Manages mask loading, caching, and processing operations.
    Handles both static masks and dynamic sequence frames based on configuration.
    """
    
    def __init__(self, config: MaskConfig, panorama_id: str, base_paths: Dict[str, Path]):
        """
        Initialize the MaskManager with configuration and paths.
        
        Args:
            config: Configuration containing gray values and their mappings
            panorama_id: ID of the panorama being processed
            base_paths: Dictionary containing all necessary path mappings
        """
        self.config = config
        self.panorama_id = panorama_id
        self.base_paths = base_paths
        self.mask_cache = {}  # Storage for static masks
        self.sequence_frames = {}  # Storage for sequence frames
        self.sequence_max_frames = {}  # Track max frame numbers for sequences
        self.results_index = 0
        
        # Create results directory
        self.results_dir = base_paths['results']
        self.results_dir.mkdir(exist_ok=True)

    def load_static_masks(self):
        """
        Load all static masks defined in configuration.
        Supports both PNG and BMP formats.
        Each mask is resized to target dimensions and converted to binary format.
        """
        print(f"\nLoading static masks for configuration: {self.config.name}")
        
        for gray_value in self.config.gray_values:
            # Check both PNG and BMP paths
            bmp_path = self.base_paths['base'] / f"{self.panorama_id}_{gray_value}.bmp"
            png_path = self.base_paths['base'] / f"{self.panorama_id}_{gray_value}.png"
            
            mask_path = bmp_path if bmp_path.exists() else png_path
            if mask_path.exists():
                mask = ImageProcessor.load_and_resize_image(mask_path)
                if mask is not None:
                    # Store in cache after ensuring binary values
                    _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
                    self.mask_cache[gray_value] = binary_mask
                    print(f"Loaded static mask for gray value {gray_value}")
                    print(f"Unique values in mask: {np.unique(binary_mask)}")

    def load_sequence_frames(self) -> int:
        """
        Load all sequence frames for each configured gray value.
        Handles multiple sequences per gray value, with multiple frames per sequence.
        
        Returns:
            Total number of frames loaded across all sequences
        """
        total_frames = 0
        
        # Process each gray value from configuration
        for gray_value in self.config.gray_values:
            gray_dir = self.base_paths['base'] / f"{self.panorama_id}_{gray_value}"
            if not gray_dir.exists():
                print(f"No sequence directory for gray value {gray_value}")
                continue
            
            self.sequence_frames[gray_value] = {}
            self.sequence_max_frames[gray_value] = {}
            
            # Find all sequence directories for this gray value
            seq_dirs = list(sorted(gray_dir.glob(f"{self.panorama_id}_{gray_value}_*")))
            if not seq_dirs:
                print(f"No sequences found for gray value {gray_value}")
                continue
                
            print(f"Found {len(seq_dirs)} sequences for gray value {gray_value}")
            
            # Process each sequence directory
            for seq_dir in seq_dirs:
                try:
                    # Extract sequence number from directory name
                    seq_num = int(seq_dir.name.split('_')[-1])
                    self.sequence_frames[gray_value][seq_num] = {}
                    
                    # Load all frames in this sequence
                    frame_files = sorted(seq_dir.glob('*.bmp'))
                    max_frame = 0
                    loaded_frames = 0
                    
                    for frame_path in frame_files:
                        try:
                            frame_num = int(frame_path.stem.split('_')[-1])
                            frame = ImageProcessor.load_and_resize_image(frame_path)
                            if frame is not None:
                                # Store resized and binarized frame
                                _, binary_frame = cv2.threshold(frame, 127, 255, cv2.THRESH_BINARY)
                                self.sequence_frames[gray_value][seq_num][frame_num] = binary_frame
                                max_frame = max(max_frame, frame_num)
                                loaded_frames += 1
                        except ValueError:
                            print(f"Warning: Invalid frame name in {frame_path}")
                            continue
                    
                    if loaded_frames > 0:
                        self.sequence_max_frames[gray_value][seq_num] = max_frame
                        total_frames += loaded_frames
                        print(f"Loaded {loaded_frames} frames for gray {gray_value} sequence {seq_num}")
                    
                except ValueError:
                    print(f"Warning: Invalid sequence directory name {seq_dir.name}")
                    continue
        
        return total_frames

    def get_frame(self, gray_value: int, seq_num: int, frame_num: int) -> Optional[np.ndarray]:
        """
        Retrieve a specific frame from sequence cache with bounds checking.
        
        Args:
            gray_value: The gray value of the sequence
            seq_num: Sequence number
            frame_num: Frame number within the sequence
            
        Returns:
            The requested frame if available, None otherwise
        """
        if gray_value not in self.sequence_frames:
            return None
            
        if seq_num not in self.sequence_frames[gray_value]:
            return None
            
        max_frame = self.sequence_max_frames[gray_value].get(seq_num, 0)
        if max_frame == 0:
            return None
            
        # Use last available frame if requested frame exceeds maximum
        actual_frame = min(frame_num, max_frame)
        return self.sequence_frames[gray_value][seq_num].get(actual_frame)

    def process_and_save(self, state: Dict[int, List[Tuple[int, int]]]) -> Optional[Path]:
        """
        Process current state and save result mask.
        Combines static masks and sequence frames based on their gray values,
        applying them in order from highest to lowest index to maintain proper layering.
        
        Args:
            state: Dictionary mapping gray values to list of (sequence_number, frame_number) tuples
            
        Returns:
            Optional[Path]: Path to the saved result file, or None if processing fails
        """
        if not state:
            print("No state provided")
            return None
            
        print(f"\nProcessing state: {state}")
            
        # Create output mask with background value
        target_size = (1280, 3840)  # height x width for numpy
        final_mask = np.full(target_size, 255, dtype=np.uint8)
        
        # Sort gray values by their corresponding indexes (highest first)
        # This ensures proper mask layering
        sorted_gray_values = sorted(
            self.config.gray_values,
            key=lambda x: self.config.gray_indexes.get(x, 0),
            reverse=True
        )
        
        print("\nProcessing order:")
        for gray_value in sorted_gray_values:
            if gray_value in self.config.gray_indexes:
                print(f"Gray value: {gray_value} -> Index: {self.config.gray_indexes[gray_value]}")
        
        # Process masks in sorted order (highest index to lowest)
        for gray_value in sorted_gray_values:
            print(f"\nProcessing gray value: {gray_value}")
            active_frames = []
            
            # Add static mask if it exists
            if gray_value in self.mask_cache:
                print(f"Found static mask for {gray_value}")
                active_frames.append(self.mask_cache[gray_value])
            
            # Add sequence frames if present in state
            if gray_value in state:
                print(f"Processing sequences for {gray_value}: {state[gray_value]}")
                for seq_num, frame_num in state[gray_value]:
                    frame = self.get_frame(gray_value, seq_num, frame_num)
                    if frame is not None:
                        print(f"Added frame {frame_num} from sequence {seq_num}")
                        active_frames.append(frame)
            
            # Combine frames if any exist for this gray value
            if active_frames:
                print(f"Combining {len(active_frames)} frames for gray value {gray_value}")
                if len(active_frames) > 1:
                    # Use maximum value at each pixel when combining multiple frames
                    combined_mask = np.maximum.reduce(active_frames)
                else:
                    combined_mask = active_frames[0]
                
                # Apply the corresponding index from configuration
                if gray_value in self.config.gray_indexes:
                    index = self.config.gray_indexes[gray_value]
                    pixels_before = np.sum(final_mask == index)
                    final_mask[combined_mask > 0] = index
                    pixels_after = np.sum(final_mask == index)
                    print(f"Set {pixels_after - pixels_before} pixels to index {index}")

        # Save the result with incremented index
        next_index = self.results_index + 1
        result_path = self.results_dir / f"{next_index}.bmp"
        print(f"\nSaving result to: {result_path}")
        cv2.imwrite(str(result_path), final_mask)
        self.results_index = next_index
        
        return result_path