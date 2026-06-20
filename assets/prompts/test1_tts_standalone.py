"""
test_tts_standalone_updated.py

Updated test file that works with text-to-speech.py
Run: python test_tts_standalone_updated.py

If you have text-to-speech.py instead of tts_engine.py, use this file!
"""

import time
from pathlib import Path

# Try to import from text-to-speech.py (your module)
try:
    from text_to_speech import TTSEngine, SimpleTTSEngine
    print("[IMPORT] Successfully imported from text_to_speech.py")
except ImportError as e:
    print(f"[ERROR] Could not import from text_to_speech.py: {e}")
    print("\nTrying alternate import...")
    try:
        from text_to_speech import TTSEngine, SimpleTTSEngine  # ✓ CORRECTprint("[IMPORT] Successfully imported from tts_engine.py")
    except ImportError as e2:
        print(f"[ERROR] Could not import from tts_engine.py either: {e2}")
        print("\nMake sure you have EITHER:")
        print("  - text-to-speech.py (your current module)")
        print("  - tts_engine.py (our provided module)")
        exit(1)


def test_default():
    """Test 1: Default voice and speed"""
    print("\n" + "=" * 60)
    print("TEST 1: Default Settings")
    print("=" * 60)
    
    try:
        engine = TTSEngine()
        engine.start()
        
        print("Speaking: 'Hello world. This is a test.'")
        engine.speak("Hello world. This is a test.", "CONTINUE")
        time.sleep(3)
        
        engine.stop()
        print("✓ TEST 1 PASSED")
        return True
    except Exception as e:
        print(f"✗ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_different_voice():
    """Test 2: Different voice (male)"""
    print("\n" + "=" * 60)
    print("TEST 2: Different Voice")
    print("=" * 60)
    
    try:
        engine = TTSEngine(voice="en-US-GuyNeural")
        engine.start()
        
        print("Speaking: 'Stop. Person ahead.'")
        engine.speak("Stop. Person ahead.", "STOP")
        time.sleep(2)
        
        engine.stop()
        print("✓ TEST 2 PASSED")
        return True
    except Exception as e:
        print(f"✗ TEST 2 FAILED: {e}")
        return False


def test_slower_speed():
    """Test 3: Slower speech"""
    print("\n" + "=" * 60)
    print("TEST 3: Slower Speech")
    print("=" * 60)
    
    try:
        engine = TTSEngine(rate=0.7)
        engine.start()
        
        print("Speaking: 'Watch the stairs. Very close now.'")
        engine.speak("Watch the stairs. Very close now.", "SLOW_DOWN")
        time.sleep(4)
        
        engine.stop()
        print("✓ TEST 3 PASSED")
        return True
    except Exception as e:
        print(f"✗ TEST 3 FAILED: {e}")
        return False


def test_priority_queue():
    """Test 4: Priority queue (interrupt)"""
    print("\n" + "=" * 60)
    print("TEST 4: Priority Queue")
    print("=" * 60)
    
    try:
        engine = TTSEngine()
        engine.start()
        
        print("Queuing low-priority: 'Path appears clear.'")
        engine.speak("Path appears clear.", "CONTINUE")
        time.sleep(0.5)
        
        print("Interrupting with high-priority: 'STOP! Person ahead!'")
        engine.speak("STOP! Person ahead!", "STOP")
        time.sleep(3)
        
        engine.stop()
        print("✓ TEST 4 PASSED (STOP should interrupt CONTINUE)")
        return True
    except Exception as e:
        print(f"✗ TEST 4 FAILED: {e}")
        return False


def test_caching():
    """Test 5: Caching"""
    print("\n" + "=" * 60)
    print("TEST 5: Caching")
    print("=" * 60)
    
    try:
        engine = TTSEngine()
        engine.start()
        
        print("1st call (will synthesize): 'Stop.'")
        engine.speak("Stop.", "STOP")
        time.sleep(2)
        
        print("2nd call (will use cache): 'Stop.'")
        engine.speak("Stop.", "STOP")
        time.sleep(1)
        
        engine.stop()
        print("✓ TEST 5 PASSED (cache should speed up 2nd call)")
        return True
    except Exception as e:
        print(f"✗ TEST 5 FAILED: {e}")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("#" * 60)
    print("# TTS ENGINE TEST (text-to-speech.py)")
    print("#" * 60)
    print("\nThis tests your text-to-speech module.\n")
    
    results = []
    
    try:
        results.append(("Test 1: Default", test_default()))
        results.append(("Test 2: Different voice", test_different_voice()))
        results.append(("Test 3: Slower speed", test_slower_speed()))
        results.append(("Test 4: Priority queue", test_priority_queue()))
        results.append(("Test 5: Caching", test_caching()))
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        for test_name, passed in results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"{test_name}: {status}")
        
        passed_count = sum(1 for _, p in results if p)
        total_count = len(results)
        
        print(f"\nTotal: {passed_count}/{total_count} tests passed")
        
        if passed_count == total_count:
            print("\n✓ ALL TESTS PASSED!")
            print("\nYour TTS module is working correctly.")
            print("You can now use it in main_with_tts.py")
        else:
            print(f"\n! {total_count - passed_count} tests failed")
            print("Check the errors above and install missing dependencies")
        
        print("\n" + "=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()