#!/usr/bin/env python3
"""
Test auto-launch missile logic
"""

class MockSwarmMaster:
    def __init__(self):
        self.auto_launch_missiles = True
        self.missile_launched = False
        self.target_data = None
        self.missiles_fired = []
    
    def launch_missile_at_target(self, launcher_vehicle_id=2, target_vehicle_id=6):
        """Mock missile launch"""
        self.missiles_fired.append({
            'launcher': launcher_vehicle_id,
            'target': target_vehicle_id
        })
        return True

def test_auto_launch_logic():
    """Test the auto-launch conditions"""
    print("\n" + "="*70)
    print("🚀 AUTO-LAUNCH LOGIC TEST")
    print("="*70 + "\n")
    
    master = MockSwarmMaster()
    
    # Test 1: Auto-launch disabled
    print("Test 1: Auto-launch disabled")
    master.auto_launch_missiles = False
    master.target_data = {'confidence': 0.85}
    if master.auto_launch_missiles and not master.missile_launched and master.target_data:
        confidence = master.target_data.get('confidence', 0)
        if confidence > 0.60:
            master.launch_missile_at_target()
    print(f"   Missiles fired: {len(master.missiles_fired)} (expected: 0)")
    assert len(master.missiles_fired) == 0, "Should not launch when disabled"
    print("   ✅ PASS\n")
    
    # Test 2: Low confidence
    print("Test 2: Low confidence (0.45 < 0.60)")
    master.auto_launch_missiles = True
    master.missile_launched = False
    master.target_data = {'confidence': 0.45}
    if master.auto_launch_missiles and not master.missile_launched and master.target_data:
        confidence = master.target_data.get('confidence', 0)
        if confidence > 0.60:
            master.launch_missile_at_target()
    print(f"   Missiles fired: {len(master.missiles_fired)} (expected: 0)")
    assert len(master.missiles_fired) == 0, "Should not launch with low confidence"
    print("   ✅ PASS\n")
    
    # Test 3: High confidence, first time
    print("Test 3: High confidence (0.85 > 0.60), first time")
    master.missiles_fired = []
    master.auto_launch_missiles = True
    master.missile_launched = False
    master.target_data = {'confidence': 0.85}
    if master.auto_launch_missiles and not master.missile_launched and master.target_data:
        confidence = master.target_data.get('confidence', 0)
        if confidence > 0.60:
            master.launch_missile_at_target()
            master.missile_launched = True
    print(f"   Missiles fired: {len(master.missiles_fired)} (expected: 1)")
    assert len(master.missiles_fired) == 1, "Should launch with high confidence"
    print("   ✅ PASS\n")
    
    # Test 4: Already launched (missile_launched flag prevents duplicate)
    print("Test 4: High confidence, but already launched")
    prev_count = len(master.missiles_fired)
    master.auto_launch_missiles = True
    master.missile_launched = True  # Already launched
    master.target_data = {'confidence': 0.95}
    if master.auto_launch_missiles and not master.missile_launched and master.target_data:
        confidence = master.target_data.get('confidence', 0)
        if confidence > 0.60:
            master.launch_missile_at_target()
    print(f"   Missiles fired: {len(master.missiles_fired)} (expected: {prev_count})")
    assert len(master.missiles_fired) == prev_count, "Should not launch duplicate"
    print("   ✅ PASS\n")
    
    # Test 5: No target data
    print("Test 5: No target detected (target_data is None)")
    master.missiles_fired = []
    master.auto_launch_missiles = True
    master.missile_launched = False
    master.target_data = None
    if master.auto_launch_missiles and not master.missile_launched and master.target_data:
        confidence = master.target_data.get('confidence', 0)
        if confidence > 0.60:
            master.launch_missile_at_target()
    print(f"   Missiles fired: {len(master.missiles_fired)} (expected: 0)")
    assert len(master.missiles_fired) == 0, "Should not launch without target data"
    print("   ✅ PASS\n")
    
    # Test 6: Threshold edge case (exactly 0.60)
    print("Test 6: Exactly at threshold (confidence = 0.60)")
    master.missiles_fired = []
    master.auto_launch_missiles = True
    master.missile_launched = False
    master.target_data = {'confidence': 0.60}
    if master.auto_launch_missiles and not master.missile_launched and master.target_data:
        confidence = master.target_data.get('confidence', 0)
        if confidence > 0.60:  # Note: > not >=
            master.launch_missile_at_target()
    print(f"   Missiles fired: {len(master.missiles_fired)} (expected: 0, since 0.60 is not > 0.60)")
    assert len(master.missiles_fired) == 0, "Should not launch at exact threshold"
    print("   ✅ PASS\n")
    
    # Test 7: Just above threshold (0.61)
    print("Test 7: Just above threshold (confidence = 0.61)")
    master.missiles_fired = []
    master.auto_launch_missiles = True
    master.missile_launched = False
    master.target_data = {'confidence': 0.61}
    if master.auto_launch_missiles and not master.missile_launched and master.target_data:
        confidence = master.target_data.get('confidence', 0)
        if confidence > 0.60:
            master.launch_missile_at_target()
            master.missile_launched = True
    print(f"   Missiles fired: {len(master.missiles_fired)} (expected: 1)")
    assert len(master.missiles_fired) == 1, "Should launch just above threshold"
    print("   ✅ PASS\n")

def main():
    print("\n🧪 AUTO-LAUNCH MISSILE LOGIC TESTS\n")
    
    try:
        test_auto_launch_logic()
        print("="*70)
        print("✅ ALL AUTO-LAUNCH TESTS PASSED")
        print("="*70 + "\n")
        return 0
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"❌ ERROR: {e}\n")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
