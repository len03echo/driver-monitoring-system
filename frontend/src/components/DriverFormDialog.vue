<template>
  <el-dialog
    v-model="visible"
    title="新增驾驶员"
    width="480px"
    :close-on-click-modal="false"
    destroy-on-close
    @closed="resetForm"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="80px"
      label-position="right"
    >
      <el-form-item label="姓名" prop="name">
        <el-input
          v-model="form.name"
          placeholder="请输入驾驶员姓名"
          maxlength="50"
          show-word-limit
          clearable
        />
      </el-form-item>
      <el-form-item label="工号" prop="employee_id">
        <el-input
          v-model="form.employee_id"
          placeholder="请输入工号（全局唯一）"
          maxlength="30"
          show-word-limit
          clearable
        />
      </el-form-item>
    </el-form>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      style="margin-top: 8px"
    >
      <template #default>
        新增后驾驶员暂无人脸特征，需通过桌面客户端完成人脸注册后方可使用身份认证功能。
      </template>
    </el-alert>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        确认新增
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  /** 提交中状态 */
  submitting: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'submit'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const formRef = ref(null)

const form = reactive({
  name: '',
  employee_id: ''
})

const rules = {
  name: [
    { required: true, message: '请输入驾驶员姓名', trigger: 'blur' },
    { min: 1, max: 50, message: '姓名长度不超过 50 个字符', trigger: 'blur' }
  ],
  employee_id: [
    { required: true, message: '请输入工号', trigger: 'blur' },
    { min: 1, max: 30, message: '工号长度不超过 30 个字符', trigger: 'blur' }
  ]
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
    emit('submit', { name: form.name, employee_id: form.employee_id })
  } catch {
    // 表单验证失败，不提交
  }
}

function resetForm() {
  form.name = ''
  form.employee_id = ''
  formRef.value?.resetFields()
}
</script>
