import vgamepad as vg
import sys
import time

def main():
    """
    A minimal script to test vgamepad and ViGEmBus driver.
    
    Type 'a', 'b', 'x', 'y' to press the corresponding button
    for 1 second.
    Press 'q' to QUIT.
    """
    
    print("--- vgamepad Test Script ---")
    print("Attempting to connect to ViGEmBus driver...")
    
    try:
        gamepad = vg.VX360Gamepad() # CORRECTED CLASS NAME
        print("Virtual Xbox 360 controller connected.")
        print("Please check 'joy.cpl' and open the controller 'Properties' window.")
    except Exception as e:
        print("\n--- ERROR ---")
        print(f"Failed to create virtual gamepad: {e}")
        print("Please ensure the ViGEmBus driver is installed correctly.")
        print("Download it from: https://github.com/ViGEm/ViGEmBus/releases/latest")
        sys.exit(1)

    print("\nControls:")
    print("  'a', 'b', 'x', 'y' - PRESS and HOLD the button for 1 second.")
    print("  'q'                - QUIT the script.")
    print("-" * 20)

    # Map user input to vgamepad buttons
    button_map = {
        'a': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
        'b': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
        'x': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
        'y': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    }

    try:
        while True:
            # Get user input
            key = input("Press key (a, b, x, y, q): ").lower()
            
            if key == 'q':
                print("Quitting...")
                break
                
            elif key in button_map:
                button_to_press = button_map[key]
                
                # --- PRESS ---
                print(f"Button '{key.upper()}' PRESSED (holding for 1 sec)...")
                gamepad.press_button(button=button_to_press)
                gamepad.update() # Send the state change
                
                # --- HOLD ---
                time.sleep(1.0)
                
                # --- RELEASE ---
                gamepad.release_button(button=button_to_press)
                gamepad.update() # Send the state change
                print(f"Button '{key.upper()}' RELEASED.")
                
            else:
                print(f"Unknown command: '{key}'")
            
    except EOFError:
        print("Input ended.")
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        # --- IMPORTANT ---
        # Clean up and disconnect the virtual controller
        print("Disconnecting virtual controller...")
        # Reset all controls to default before deleting
        gamepad.reset()
        gamepad.update()
        del gamepad
        print("Done.")

if __name__ == "__main__":
    main()