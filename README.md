# Generate Certificate XBlock

![https://github.com/eol-uchile/generate_certificate_xblock/actions](https://github.com/eol-uchile/generate_certificate_xblock/workflows/Python%20application/badge.svg)

# Install

    docker-compose exec cms pip install -e /openedx/requirements/generate_certificate_xblock
    docker-compose exec lms pip install -e /openedx/requirements/generate_certificate_xblock

## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run --rm lms /openedx/requirements/generate_certificate_xblock/.github/test.sh

