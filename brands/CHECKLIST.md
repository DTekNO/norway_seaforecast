# Home Assistant Brands Submission Checklist

## Pre-Submission Checklist

Before submitting to the Home Assistant Brands repository, verify:

### File Requirements

- [ ] `icon.png` exists and is exactly 256x256 pixels
- [ ] `icon.png` has a transparent background
- [ ] `icon.png` file size is under 50KB (preferably under 10KB)
- [ ] Icon is visible and clear at small sizes (32x32, 48x48)

### Optional Files

- [ ] `icon@2x.png` exists for dark mode (256x256px, transparent)
- [ ] `logo.png` exists (256x128px, transparent) - if you want a horizontal version
- [ ] All files are optimized with optipng or pngquant

### Submission Process

1. [ ] Fork the repository: https://github.com/home-assistant/brands

2. [ ] Create the folder structure:
   ```
   brands/custom_integrations/havvarsel/
   ```

3. [ ] Copy your PNG file(s) to the folder

4. [ ] Test locally by placing files in Home Assistant and viewing the integration

5. [ ] Create Pull Request with clear title: "Add Havvarsel integration logos"

6. [ ] In PR description, mention:
   - [ ] Integration name: Havvarsel
   - [ ] Integration purpose: Norwegian sea/ocean condition warnings
   - [ ] Domain: `havvarsel`
   - [ ] Repository: https://github.com/DTekNO/ha-havvarsel-custom-integration

### PR Description Template

```markdown
## Add Havvarsel integration logos

This PR adds brand assets for the Havvarsel custom integration.

**Integration Details:**
- **Name**: Havvarsel
- **Domain**: `havvarsel`
- **Repository**: https://github.com/DTekNO/ha-havvarsel-custom-integration
- **Purpose**: Provides Norwegian sea and ocean condition warnings from the Norwegian Meteorological Institute

**Files Included:**
- `icon.png` (256x256, transparent)
- `icon@2x.png` (256x256, transparent, dark mode variant) - optional
- `logo.png` (256x128, transparent) - optional

**Design**: The logo features an "H" representing Havvarsel with wave patterns symbolizing ocean conditions.

All files have been optimized and tested in Home Assistant.
```

## Post-Submission

- [ ] Monitor PR for feedback from Home Assistant team
- [ ] Make requested changes if any
- [ ] Once merged, update integration documentation to mention official branding support

## Notes

- The Home Assistant Brands team usually responds within a few days
- Be prepared to make adjustments if requested
- The review process ensures consistency across all Home Assistant integrations
