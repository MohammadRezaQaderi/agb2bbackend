# PSY workbook packages

The PSY quiz definitions and scoring maps are generated from the source
`exams.xlsx` workbooks. Excel and `openpyxl` are not used by the application at
runtime.

Compile a source release with an immutable version:

```bash
python scripts/compile_psy_workbooks.py /path/to/finalexams/exams \
  --version v1 \
  --assets-output /path/from/AG_QUIZ_PIC_DIR
```

The command:

- discovers every numbered folder containing `exams.xlsx`;
- gives each package a canonical `PSY_*` name;
- validates question IDs, answer counts, scores, and referenced images;
- writes versioned Python data under `quiz_packages/psy/versions/`;
- updates `generated_manifest.py` to select the newly compiled version;
- converts Raven question and answer images to the flat `.JPG` names expected
  by the student frontend.

When source workbooks change, compile them under a new version such as `v2`.
Do not overwrite an old generated version that may be referenced by existing
quiz attempts. Restart the API after deploying the generated files and assets.

If `--assets-output` is omitted, all referenced assets are still validated but
are not copied. This is useful in CI and when only text packages changed.
