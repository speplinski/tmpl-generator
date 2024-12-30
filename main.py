#!/usr/bin/env python3

import argparse
from typing import List

from tmpl_generator.configs.mask_config import MaskConfig
from tmpl_generator.core.tmpl_monitor import TMPLMonitor
from tmpl_generator.core.system_monitor import SystemMonitor
from tmpl_generator.utils.dynamic_config import create_dynamic_config

def parse_arguments():
    parser = argparse.ArgumentParser(description='TMPL Mask Generation System')
    parser.add_argument('panorama_id', help='ID of the panorama to process')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    print(f"\nInitializing TMPL Generator: {args.panorama_id}")
    
    print("\nStarting memory status:")
    SystemMonitor.print_memory_status()
    
    # Create dynamic configuration based on directory content
    config = create_dynamic_config(args.panorama_id)
    mask_configs = [MaskConfig(**config)]
    
    # Initialize and run the monitor
    monitor = TMPLMonitor(args.panorama_id, mask_configs)
    monitor.run()

if __name__ == "__main__":
    main()