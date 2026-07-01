# Bug Fix: User ID Extraction Issue

## Problem Summary
The SDUI Timetable integration was extracting the wrong user_id from the JWT token, causing the API to fetch data for the wrong user. This resulted in empty sensors even though the integration appeared to be working.

## Root Cause
The JWT token's `sub` claim contains an account ID (e.g., `9876543`) that differs from the timetable user_id visible in the SDUI web URL (e.g., `1234567`). The integration was auto-extracting the `sub` claim and using it as the timetable user_id, which failed to return any lesson data.

## Evidence
```
User's timetable URL: https://sdui.app/timetable/users/1234567
API call made by integration: https://api.sdui.app/v1/timetables/users/9876543/timetable
Result: Empty lessons (fetching wrong user's data)
```

## Solution Implemented

### 1. Updated Config Flow (config_flow.py)
- **Before:** Auto-extracted user_id from JWT token
- **After:** Added user_id as a required input field
- Users must now provide their user_id manually (found in their SDUI timetable URL)

### 2. Updated API Client (api.py)
- **Before:** Always extracted user_id from token in `__init__()`
- **After:** Accepts optional `user_id` parameter, falls back to token extraction if not provided (backward compatibility)

### 3. Updated Integration Setup (__init__.py)
- Now passes `user_id` from config entry to API client
- Maintains backward compatibility with old config entries

### 4. Updated Options Flow (config_flow.py)
- Added user_id field to options
- Users can now update both token and user_id via "Configure" button

## Files Modified
- `custom_components/sdui_timetable/config_flow.py`
- `custom_components/sdui_timetable/api.py`
- `custom_components/sdui_timetable/__init__.py`

## Migration Steps for Users

### For New Installations:
1. Install integration via HACS
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration → Search "Sdui"
4. Enter both:
   - Bearer token
   - User ID (from your SDUI timetable URL)
5. Submit

### For Existing Installations (Breaking Change):
1. **Remove the old integration:**
   - Settings → Devices & Services
   - Find "Sdui" or "SDUI Timetable"
   - Click three dots → Delete

2. **Restart Home Assistant**

3. **Re-add the integration:**
   - Settings → Devices & Services → Add Integration
   - Search "Sdui"
   - Enter your bearer token
   - **Enter your user_id from your SDUI URL:**
     - Go to https://sdui.app/timetable
     - Copy the number from the URL: `https://sdui.app/timetable/users/YOUR_USER_ID`
   - Submit

4. **Verify it works:**
   - Check Developer Tools → States → sensor.sdui_lessons_today
   - Should now show your actual lessons

## Finding Your User ID

Your user_id is in your SDUI timetable URL:

```
https://sdui.app/timetable/users/1234567
                                 ^^^^^^^
                                 This is your user_id
```

Steps to find it:
1. Log in to https://sdui.app
2. Navigate to your timetable
3. Look at the URL in your browser
4. Copy the number after `/users/`

## Backward Compatibility

The API client maintains backward compatibility:
- **New config entries:** Use the provided user_id
- **Old config entries (if any):** Fall back to JWT extraction (may not work correctly)
- **Recommendation:** All users should delete and re-add the integration with the correct user_id

## Testing Checklist

After re-adding the integration:
- [ ] Integration loads without errors
- [ ] Sensors are created (sensor.sdui_lessons_today, etc.)
- [ ] Sensors show correct data (not empty on weekdays)
- [ ] Calendar shows your lessons
- [ ] Automation triggers when sensors update
- [ ] Logs show correct API URL with your user_id

## Known Issues Resolved

✅ Empty sensors on weekdays (wrong user_id)
✅ "Config flow could not be loaded" error (domain mismatch - separate fix)
✅ Integration silently failing (no error logs)

## Additional Notes

This bug affected users with:
- Parent accounts managing student timetables
- Teacher accounts
- Multi-user accounts
- Any scenario where JWT `sub` claim ≠ timetable user_id

The fix requires manual user_id input, which is more reliable and transparent than automatic extraction from the JWT token.