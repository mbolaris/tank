@echo off
cd /d c:\shared\bolaris\tank
git add -A
git commit -m "Fixes: genome serialization compatibility, trait clamping, remove legacy screen args, fix spawn_auto_food syntax

- Accept legacy genome kwargs (behavior_algorithm, poker_algorithm) in codec
- Clamp trait values during deserialization to TraitSpec bounds
- Add defensive checks in Genome computed properties
- Remove legacy screen_width/screen_height kwargs from spawn/add-food call sites and tests
- Fix unmatched parenthesis in spawn_auto_food method"
echo.
git log --oneline -1
pause
