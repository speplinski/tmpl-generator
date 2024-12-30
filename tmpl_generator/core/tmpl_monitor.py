from pathlib import Path
from typing import List
import time
from datetime import datetime

from tmpl_generator.configs.mask_config import MaskConfig
from tmpl_generator.utils.constants import MONITORING_INTERVAL
from .system_monitor import SystemMonitor
from .file_monitor import FileMonitor
from .mask_manager import MaskManager

class TMPLMonitor:
    """Main monitoring system"""
    def __init__(self, panorama_id: str, mask_configs: List[MaskConfig]):
        self.panorama_id = panorama_id
        
        # Setup paths
        self.base_paths = {
            'base': Path(f'./landscapes/{panorama_id}'),
            'sequences': Path(f'./landscapes/{panorama_id}/sequences'),
            'output': Path(f'./landscapes/{panorama_id}'),
            'results': Path('./results')
        }
        self.base_paths['results'].mkdir(exist_ok=True)
        
        # Initialize components
        self.file_monitor = FileMonitor('tmpl.log')
        self.mask_managers = {
            config.name: MaskManager(config, panorama_id, self.base_paths)
            for config in mask_configs
        }
        
        self._initialize_system()

    def _initialize_system(self):
        """Initialize system"""
        print("Initializing system...")
        print("\nInitial memory status:")
        SystemMonitor.print_memory_status()
        
        # Load static masks and sequence frames for each configuration
        for manager in self.mask_managers.values():
            manager.load_static_masks()
            print(f"\nMemory status after loading {manager.config.name} masks:")
            SystemMonitor.print_memory_status()
        
        print("\nLoading sequence frames...")
        total_frames = next(iter(self.mask_managers.values())).load_sequence_frames()
        print(f"\nTotal frames loaded: {total_frames}")
        print("\nFinal memory status:")
        SystemMonitor.print_memory_status()

    def process_state(self, state: List[int]):
        """Process state for all configurations"""
        if not state or not any(state):
            return

        process_start = time.time()
        current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\nStarting processing at: {current_time}")
        print("Memory before processing:")
        SystemMonitor.print_memory_status()

        try:
            active_sequences = []
            for seq_num, frame_num in enumerate(state):
                if frame_num > 0:
                    active_sequences.append((seq_num, frame_num))
            
            state_dict = {}
            
            # Process each configuration
            for name, manager in self.mask_managers.items():
                config_start = time.time()
                print(f"\nProcessing {name} configuration...")
            
                config_state = {}
                for gray_value in manager.config.gray_values:
                    config_state[gray_value] = active_sequences
            
                result_path = manager.process_and_save(config_state)
                if result_path:
                    config_time = time.time() - config_start
                    print(f"Result saved as: {result_path}")
                    print(f"Configuration processing time: {config_time:.3f}s")
                else:
                    print("No valid frames to process")
        
            total_time = time.time() - process_start
            current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
            print(f"\nAll processing completed at: {current_time}")
            print(f"Total processing time: {total_time:.3f}s")
        
            print("\nMemory after processing:")
            SystemMonitor.print_memory_status()
        
        except Exception as e:
            print(f"Error in processing: {e}")
            raise

    def run(self):
        """Main program loop"""
        print("\nTMPL Monitor Started")
        print("Waiting for updates...")
        
        try:
            while True:
                try:
                    new_state, updated = self.file_monitor.check_for_updates()
                    if updated and new_state:
                        self.process_state(new_state)
                    time.sleep(MONITORING_INTERVAL)

                except KeyboardInterrupt:
                    print("\nMonitor stopped.")
                    break
                except Exception as e:
                    print(f"Error: {e}")
                    time.sleep(MONITORING_INTERVAL)
                    
        except KeyboardInterrupt:
            print("\nShutting down...")