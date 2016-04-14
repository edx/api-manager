build-api:
	swagger-codegen generate -l swagger -i swagger/api.yaml -o build-output

.PHONY: build-swagger
