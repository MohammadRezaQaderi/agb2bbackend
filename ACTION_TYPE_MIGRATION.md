# Frontend action_type migration for AG/AGS

This is the source of truth for migrating AG and AGS frontend calls to the new
ERBackend-style API contract.

Old action names are no longer accepted by the backend. Every `/ag_api/*` and
`/ags_api/*` request must send the new `action_type` values listed below and
must wrap payloads in `request_data`.

## Required request wrapper

Owner/consultant/institute/school requests under `/ag_api/*` use `ag_*`
action names:

```json
{
  "action_type": "ag_get_dashboard",
  "request_data": {
    "user_id": 1,
    "token": "..."
  }
}
```

Student requests under `/ags_api/*` use the same wrapper shape, but with
student-scoped `ags_*` action names:

```json
{
  "action_type": "ags_get_dashboard",
  "request_data": {
    "user_id": 1,
    "token": "..."
  }
}
```

Admin requests keep the admin token at the top level:

```json
{
  "token": "...",
  "action_type": "ag_get_user_info",
  "request_data": {
    "phone": "09120000000"
  }
}
```

## Migration rules

1. Replace legacy `method_type` with `action_type`.
2. Replace legacy top-level request payload fields with `request_data`.
3. Replace every old action name with the matching required action name in the
   endpoint tables below.
4. Keep admin tokens at the top level for `/ag_api/admin_request`.
5. Do not keep compatibility branches for old action names in frontend code.

## Internal service method names

These are backend method renames only. Frontend should use the `action_type` values in the endpoint sections below.

| Old method | New method |
| --- | --- |
| `services.auth.auth_service.token_remove` | `services.auth.auth_service.remove_token` |
| `services.auth.auth_service.check_signin` | `services.auth.auth_service.sign_in` |
| `services.auth.auth_service.check_signup` | `services.auth.auth_service.sign_up` |
| `services.auth.auth_service.check_send_sms` | `services.auth.auth_service.send_otp` |
| `services.auth.auth_service.check_sms_verify` | `services.auth.auth_service.check_otp` |
| `services.service.delete_token` | `services.service.remove_token` |
| `services.service.signin` | `services.service.sign_in` |
| `services.service.signup` | `services.service.sign_up` |
| `services.service.update_user` | `services.service.change_user_info` |
| `services.service.update_password` | `services.service.change_password` |
| `services.service.update_setting` | `services.service.change_setting` |
| `services.service.update_student_access` | `services.service.change_student_access` |
| `services.service.update_user_quiz_setting` | `services.service.change_user_quiz_setting` |
| `services.service.select_dashboard` | `services.service.get_dashboard` |
| `services.service.select_consultants` | `services.service.get_consultants` |
| `services.service.insert_consultant` | `services.service.add_consultant` |
| `services.service.update_consultant` | `services.service.change_consultant` |
| `services.service.select_students` | `services.service.get_students` |
| `services.service.select_report_data` | `services.service.get_report_data` |
| `services.service.insert_student` | `services.service.add_student` |
| `services.service.update_student` | `services.service.change_student` |
| `services.service.make_comment` | `services.service.change_comment` |
| `services.service.select_quiz_setting` | `services.service.get_quiz_setting` |
| `services.service.select_report` | `services.service.get_report` |
| `services.service.select_management_report` | `services.service.get_management_report` |
| `services.service.select_quiz_info` | `services.service.get_quiz_info` |
| `services.service.get_users_transactions` | `services.service.get_transactions` |
| `services.service.insert_order_payment` | `services.service.add_payment_order` |
| `services.service.select_comments` | `services.service.get_comments` |
| `services.service.insert_comment` | `services.service.add_comment` |
| `services.service.admin_update_capacity` | `services.service.admin_change_capacity` |
| `services.other.other_service.select_all_products` | `services.other.other_service.get_all_products` |
| `services.other.other_service.select_users_transactions` | `services.other.other_service.get_transactions` |
| `services.admin.admin_service.update_capacity` | `services.admin.admin_service.change_capacity` |

Role service files now use the same local vocabulary:

| Old pattern | New pattern |
| --- | --- |
| `select_*_info` | `get_info` |
| `select_*_dashboard` | `get_dashboard` |
| `select_*_report` | `get_report` |
| `select_*_management_report` | `get_management_report` |
| `select_*_consultant` | `get_consultants` |
| `select_*_student` | `get_students` |
| `insert_*_consultant` | `add_consultant` |
| `insert_*_student` | `add_student` |
| `insert_institute` | `add_institute` |
| `insert_school` | `add_school` |
| `insert_owner_consultant` | `add_owner_consultant` |
| `update_*_consultant` | `change_consultant` |
| `update_*_student` | `change_student` |
| `update_*_comment` | `change_comment` |
| `update_*_user_profile` | `change_user_info` |
| `update_user_*_pic` | `change_user_image` |
| `update_user_*_voice` | `change_user_voice` |
| `update_*_setting` | `change_setting` |
| `update_*_verify` | `verify_user` |
| `update_*_student_access` | `change_student_access` |

## /ag_api/signin

| Legacy action_type | Required action_type |
| --- | --- |
| `signin` | `ag_sign_in` |

## /ag_api/insert_request

| Legacy action_type | Required action_type |
| --- | --- |
| `signup` | `ag_sign_up` |
| `send_otp` | `ag_send_otp` |
| `insert_comment` | `ag_add_comment` |
| `insert_order_payment` | `ag_add_payment_order` |
| `insert_consultant` | `ag_add_consultant` |
| `insert_student` | `ag_add_student` |
| `mark_notification_read` | `ag_mark_notification_read` |

## /ag_api/select_request

| Legacy action_type | Required action_type |
| --- | --- |
| `check_otp` | `ag_check_otp` |
| `select_comments` | `ag_get_comments` |
| `select_dashboard` | `ag_get_dashboard` |
| `select_consultants` | `ag_get_consultants` |
| `select_students` | `ag_get_students` |
| `select_report` | `ag_get_report` |
| `select_management_report` | `ag_get_management_report` |
| `select_quiz_setting` | `ag_get_quiz_setting` |
| `select_quiz_info` | `ag_get_quiz_info` |
| `apply_discount` | `ag_apply_discount` |
| `select_users_transactions` | `ag_get_transactions` |
| `select_report_data` | `ag_get_report_data` |

## /ag_api/update_request

| Legacy action_type | Required action_type |
| --- | --- |
| `update_user` | `ag_change_user_info` |
| `update_password` | `ag_change_password` |
| `update_setting` | `ag_change_setting` |
| `update_consultant` | `ag_change_consultant` |
| `update_student` | `ag_change_student` |
| `update_comment` | `ag_change_comment` |
| `update_user_quiz_setting` | `ag_change_user_quiz_setting` |
| `update_student_access` | `ag_change_student_access` |

## /ag_api/delete_request

| Legacy action_type | Required action_type |
| --- | --- |
| `delete_token` | `ag_remove_token` |

## /ag_api/admin_request

| Legacy action_type | Required action_type |
| --- | --- |
| `update_capacity` | `ag_change_capacity` |
| `get_user_info` | `ag_get_user_info` |
| `check_student_quiz_answer` | `ag_check_student_quiz_answer` |

## /ag_api/update_user_file_image

| Legacy action_type | Required action_type |
| --- | --- |
| `update_user` | `ag_change_user_info` |
| `update_user_file_image` | `ag_change_user_image` |

## /ags_api/signin

| Legacy action_type | Required action_type |
| --- | --- |
| `signin` | `ags_sign_in` |

## /ags_api/select_request

| Legacy action_type | Required action_type |
| --- | --- |
| `select_dashboard` | `ags_get_dashboard` |
| `select_quiz_setting` | `ags_get_quiz_setting` |
| `select_access_product` | `ags_get_access_product` |
| `select_quiz_table_info` | `ags_get_quiz_table_info` |
| `select_quiz_info` | `ags_get_quiz_info` |

## /ags_api/update_request

| Legacy action_type | Required action_type |
| --- | --- |
| `update_user` | `ags_change_user_info` |
| `update_password` | `ags_change_password` |
| `update_quiz_answer` | `ags_change_quiz_answer` |

## /ags_api/delete_request

| Legacy action_type | Required action_type |
| --- | --- |
| `delete_token` | `ags_remove_token` |

## Static GET endpoints

These endpoints do not use `action_type`; they are direct `GET` routes and are
available under both `/ag_api` and `/ags_api`:

| Endpoint |
| --- |
| `/ag_api/majors` |
| `/ags_api/majors` |
| `/ag_api/majors/{major_id}/categories` |
| `/ags_api/majors/{major_id}/categories` |
| `/ag_api/fields/{field_id}` |
| `/ags_api/fields/{field_id}` |
