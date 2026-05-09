#!/usr/bin/env python3
"""
Task Manager Module
Slave'lere görev atama ve yönetimi
"""


class TaskManager:
    """Slave araçlara görev atar ve yönetir."""
    
    def __init__(self):
        self.slave_tasks = {
            2: "REAR_GUARD_LEFT",    # Slave 2: Enemy'nin sol arkası
            3: "REAR_GUARD_RIGHT",   # Slave 3: Enemy'nin sağ arkası
            4: "FLANK_LEFT",         # Slave 4: Sol flanş
            5: "FLANK_RIGHT",        # Slave 5: Sağ flanş
        }
        self.task_history = {}
        self.active_tasks = {}
    
    def assign_rear_guard_tasks(self, slave_vehicles, rear_positions, has_valid_position_func):
        """Slave 2 ve 3'e enemy'nin arkasına gitme görevini ata.
        
        Args:
            slave_vehicles: dict - slave_id -> vehicle
            rear_positions: tuple - (rear_left_location, rear_right_location)
            has_valid_position_func: Position kontrol function
        """
        rear_left, rear_right = rear_positions
        
        if not rear_left or not rear_right:
            return False
        
        positions = {
            2: rear_left,
            3: rear_right
        }
        
        for slave_id in [2, 3]:
            slave = slave_vehicles.get(slave_id)
            if not slave:
                continue
            
            if not has_valid_position_func(slave):
                print(f"[TASK] Slave {slave_id}: Position not ready, skipping")
                continue
            
            target_location = positions[slave_id]
            task = self.slave_tasks[slave_id]
            
            try:
                slave.simple_goto(target_location)
                self.active_tasks[slave_id] = {
                    'type': task,
                    'target': (target_location.lat, target_location.lon, target_location.alt)
                }
                print(
                    f"[TASK] Slave {slave_id}: {task} → "
                    f"({target_location.lat:.6f}, {target_location.lon:.6f}) "
                    f"alt={target_location.alt:.1f}m"
                )
            except Exception as e:
                print(f"[TASK] Slave {slave_id} assignment failed: {e}")
        
        return True
    
    def get_task_status(self):
        """Tüm görevlerin durumunu döndür."""
        return {
            'active_tasks': self.active_tasks,
            'task_definitions': self.slave_tasks
        }
    
    def clear_active_tasks(self):
        """Aktif görevleri temizle."""
        self.active_tasks.clear()
