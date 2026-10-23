<script setup lang="ts">
import { onLaunch, onShow, onHide } from "@dcloudio/uni-app";
import { installAuthInterceptors } from "@/utils/guard";

onLaunch(() => {
  installAuthInterceptors();
  console.info("H5 App Launch");
});
onShow(() => {
  console.info("H5 App Show");
});
onHide(() => {
  console.info("H5 App Hide");
});
</script>

<style lang="scss">
@import "@/styles/common.scss";
</style>
