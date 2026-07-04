// Source: CodeSearchNet javascript test split
// Repository: axios/axios
// Function: createInstance
// Documentation: Create an instance of Axios

@param {Object} defaultConfig The default config for the instance
@return {Axios} A new instance of Axios
function createInstance(defaultConfig) {
  var context = new Axios(defaultConfig);
  var instance = bind(Axios.prototype.request, context);

  // Copy axios.prototype to instance
  utils.extend(instance, Axios.prototype, context);

  // Copy context to instance
  utils.extend(instance, context);

  return instance;
}
