# Amazon Appstore listing – Street Noise Recorder

Copy each field into the Amazon Developer Console. Files to upload are in this `store/` folder.

## Upload files

| Console field | File |
|---|---|
| App file (APK) | `android-recorder/app/build/outputs/apk/release/app-release.apk` |
| Small icon (114×114) | `store/icon-114.png` |
| Large icon (512×512) | `store/icon-512.png` |
| Screenshots (1024×600) | `store/screenshot-1-status.png`, `screenshot-2-settings.png`, `screenshot-3-settings-detection.png`, `screenshot-4-welcome.png` |

## General information

- **App title:** Street Noise Recorder
- **Category:** Utilities
- **Price:** Free
- **Privacy policy URL:** https://github.com/DrewThomasson/sound-monitor/blob/main/docs/privacy-policy.md
  (works once the `noise-analysis` branch is merged into `main`)

## Short description

Turn a spare Fire tablet into a 24/7 street noise monitor. It saves a video with sound of every loud event, such as cars revving at night, and uploads the evidence to your own Hugging Face dataset.

## Long description

Loud cars revving their engines at 2 AM? Street Noise Recorder turns a spare Fire tablet into a round-the-clock noise monitor, so you can document the problem and bring real evidence to your city.

Mount the tablet by a window or on a balcony facing the street, plug it in, and leave it. The app:

• Listens all the time and learns your street's normal background level, so it adapts to your spot.
• Saves a short video with sound of every loud event, starting a couple of seconds before the noise.
• Logs the sound level every second, so you can show exactly when it was recording.
• Uploads everything twice a day to a Hugging Face dataset in your own account, deleting each file from the tablet only after it's safely uploaded.
• Keeps running with the screen off, warns you if the tablet gets hot or runs low on space, and resumes after a restart.

Your recordings go only to your own Hugging Face account. No ads, no tracking, and nothing is sent to the developer. The app is free and open source.

What you need:
• A Fire tablet (or other Android device) with a camera and microphone
• A wall charger
• A free Hugging Face account, dataset and write token (Settings links to each)

Please point the camera at the street, not into homes, and check your local laws on recording.

## Product feature bullets

- Records loud street noise around the clock, with video and sound
- Adapts to your street's normal background level
- Logs the sound level every second
- Uploads twice a day to your own Hugging Face dataset
- Runs unattended with the screen off and resumes after restarts
- Free and open source, with no ads or tracking

## Keywords

noise, noise pollution, decibel, sound meter, loud cars, street noise, recorder, evidence, revving, city

## Content rating answers

The app contains no violence, sexual content, profanity, gambling, drugs or alcohol, and no ads or in-app purchases.
It **does** use the camera and microphone and can upload recordings to the user's own account, so answer "yes" if
asked whether the app collects or shares user data, and point to the privacy policy.

## Device support

Fire tablets and Android phones and tablets running Android 5.0 or newer, with a camera and microphone.
